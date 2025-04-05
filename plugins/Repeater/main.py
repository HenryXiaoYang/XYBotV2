import os
import time
import json
import tomllib
from typing import Dict, List, Set, Optional, Any
from loguru import logger
import asyncio

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase


class ChatSession:
    """聊天会话类，使用简单消息列表管理每个聊天的消息"""
    
    def __init__(self, max_history: int = 50):
        self.messages: List[Dict[str, Any]] = []  # 所有消息列表
        self.max_history = max_history  # 历史记录最大长度
        self.repeated_contents: Set[str] = set()  # 已被复读过的内容集合
        self.repeated_msgs: Dict[str, Dict[str, Any]] = {}  # 机器人复读的消息信息 {content: msg_info}
    
    def add_message(self, **msg_info) -> Dict[str, Any]:
        """添加一条消息到历史记录"""
        # 添加消息到列表
        self.messages.append(msg_info)
        
        # 如果超过最大长度，删除最早的消息
        if len(self.messages) > self.max_history:
            self.messages.pop(0)
            
        return msg_info
    
    def should_repeat(self, content: str, bot_wxid: str, min_repeat_count: int = 2, min_users: int = 2) -> bool:
        """判断是否应该复读消息"""
        # 如果已经复读过，不再复读
        if content in self.repeated_contents:
            return False
            
        # 统计相同内容的消息数量和发送者
        same_content_count = 0
        senders = set()
        
        for msg in self.messages:
            if msg.get("content") == content:
                same_content_count += 1
                senders.add(msg.get("sender_wxid"))
        
        # 判断是否满足复读条件
        return (same_content_count >= min_repeat_count and 
                len(senders) >= min_users and 
                bot_wxid not in senders)
    
    def mark_as_repeated(self, content: str, revoke_info: Dict[str, Any] = None) -> None:
        """标记消息已被复读，并保存撤回信息"""
        self.repeated_contents.add(content)
        if revoke_info:
            self.repeated_msgs[content] = revoke_info
    
    def is_content_repeated(self, content: str) -> bool:
        """检查内容是否已被复读过"""
        return content in self.repeated_contents
    
    def find_message_by_new_msg_id(self, new_msg_id: int) -> Optional[Dict[str, Any]]:
        """根据消息的 new_msg_id 查找消息"""
        for msg in reversed(self.messages):  # 从最新消息开始查找
            if msg.get("new_msg_id") == new_msg_id:
                return msg
        return None
    
    def get_repeated_msg_info(self, content: str) -> Optional[Dict[str, Any]]:
        """获取机器人复读消息的撤回信息"""
        return self.repeated_msgs.get(content)


class Repeater(PluginBase):
    description = "复读机插件"
    author = "Assistant"
    version = "1.2.0"

    def __init__(self):
        super().__init__()
        self.enable = False
        self._load_config()

    def _load_config(self) -> None:
        """加载配置文件"""
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        
        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)
                
            # 读取基本配置
            basic_config = config.get("basic", {})
            self.enable = basic_config.get("enable", False)

            # 读取复读机配置
            repeater_config = config.get("repeater", {})
            self.cache_timeout = repeater_config.get("cache_timeout", 3600)
            self.enable_in_group = repeater_config.get("enable_in_group", True)
            self.enable_in_private = repeater_config.get("enable_in_private", False)
            self.max_history = repeater_config.get("max_history", 50)
            self.min_repeat_count = repeater_config.get("min_repeat_count", 2)
            self.min_different_users = repeater_config.get("min_different_users", 2)

            # 初始化聊天会话缓存 {wxid: ChatSession}
            self.chat_sessions: Dict[str, ChatSession] = {}

            logger.info("🤖 [Repeater] \x1b[32m加载配置成功\x1b[0m")

        except Exception as e:
            logger.error("🤖 [Repeater] \x1b[31m加载配置失败: {}\x1b[0m", str(e))
            self.enable = False

    async def async_init(self):
        return

    def _clean_expired_sessions(self, current_time: float) -> None:
        """清理过期的聊天会话"""
        expired_wxids = []
        
        for wxid, session in self.chat_sessions.items():
            # 检查是否有消息
            if not session.messages:
                expired_wxids.append(wxid)
                continue
                
            # 找出最新消息的时间戳
            latest_timestamp = max(msg.get("timestamp", 0) for msg in session.messages)
            if current_time - latest_timestamp > self.cache_timeout:
                expired_wxids.append(wxid)
        
        for wxid in expired_wxids:
            del self.chat_sessions[wxid]
            logger.debug("🤖 [Repeater] 清理过期会话: {}", wxid)

    def _get_or_create_session(self, wxid: str) -> ChatSession:
        """获取或创建聊天会话"""
        if wxid not in self.chat_sessions:
            self.chat_sessions[wxid] = ChatSession(max_history=self.max_history)
        return self.chat_sessions[wxid]

    def _should_process_message(self, message: dict) -> bool:
        """判断是否应该处理消息"""
        if not self.enable:
            logger.info("🤖 [Repeater] \x1b[33m插件未启用\x1b[0m")
            return False

        # 检查是否在对应场景启用
        is_group = message.get("IsGroup", False)
        if (is_group and not self.enable_in_group) or (not is_group and not self.enable_in_private):
            return False
            
        return True
    
    async def _handle_message_common(self, bot: WechatAPIClient, message: dict, 
                                    content: str, is_emoji: bool = False, 
                                    emoji_md5: str = "", emoji_length: int = 0) -> bool:
        """处理通用消息逻辑"""
        if not self._should_process_message(message):
            return True
        
        # 提取消息基本信息
        from_wxid = message.get("FromWxid", "")
        sender_wxid = message.get("SenderWxid", "")
        current_time = time.time()
        new_msg_id = message.get("NewMsgId", 0)
        
        # 清理过期缓存
        self._clean_expired_sessions(current_time)
        
        # 获取或创建聊天会话
        session = self._get_or_create_session(from_wxid)
        
        # 构建消息信息字典
        msg_info = {
            "content": content,
            "sender_wxid": sender_wxid,
            "timestamp": current_time,
            "new_msg_id": new_msg_id,
            "is_emoji": is_emoji
        }
        
        # 添加消息到历史记录
        session.add_message(**msg_info)
        
        # 检查是否已复读过
        if session.is_content_repeated(content):
            msg_type = "emoji" if is_emoji else "文本"
            logger.info("🤖 [Repeater] {}消息已复读过，跳过: {}", msg_type, content)
            return True
        
        # 检查是否应该复读
        if session.should_repeat(content, bot.wxid, self.min_repeat_count, self.min_different_users):
            msg_type = "emoji" if is_emoji else "文本"
            try:
                logger.info("🤖 [Repeater] 准备复读{}消息: {}", msg_type, content if not is_emoji else emoji_md5)
                
                # 发送消息
                if is_emoji:
                    # 发送emoji消息并保存撤回所需信息
                    create_time = int(time.time())  # 记录发送时的时间戳，用于后续撤回
                    emoji_result = await bot.send_emoji_message(from_wxid, emoji_md5, emoji_length)
                    
                    # 直接保存emoji消息撤回所需参数
                    session.mark_as_repeated(content, {
                        "msg_id": emoji_result[0]["msgId"],
                        "create_time": create_time,
                        "new_msg_id": emoji_result[0]["newMsgId"]
                    })
                else:
                    # 发送文本消息
                    client_msg_id, create_time, new_msg_id = await bot.send_text_message(from_wxid, content)
                    session.mark_as_repeated(content, {
                        "msg_id": client_msg_id,
                        "create_time": create_time,
                        "new_msg_id": new_msg_id
                    })
            except Exception as e:
                logger.error("🤖 [Repeater] \x1b[31m复读{}失败: {}\x1b[0m", msg_type, str(e))
            finally:
                logger.success("🤖 [Repeater] \x1b[32m复读{}消息成功\x1b[0m", msg_type)
        
        return True

    @on_text_message(priority=90)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        """处理文本消息"""
        content = message.get("Content", "").strip()
        return await self._handle_message_common(bot, message, content)
    
    @on_quote_message(priority=99)
    async def handle_quote(self, bot: WechatAPIClient, message: dict):
        """处理引用消息"""
        return await self.handle_text(bot, message)
    
    @on_at_message(priority=99)
    async def handle_at(self, bot: WechatAPIClient, message: dict):
        """处理@消息"""
        return await self.handle_text(bot, message)
    
    @on_emoji_message(priority=99)
    async def handle_emoji(self, bot: WechatAPIClient, message: dict):
        """处理表情消息"""
        # 获取emoji信息
        emoji_info = message.get("Emoji", {})
        emoji_md5 = emoji_info.get("Md5", "")
        emoji_length = emoji_info.get("Length", 0)
        
        # 使用emoji的MD5值作为内容标识
        content = f"emoji:{emoji_md5}"
        
        return await self._handle_message_common(
            bot, message, content, True, emoji_md5, emoji_length
        )
    
    @on_revoke_message(priority=99)
    async def handle_revoke(self, bot: WechatAPIClient, message: dict):
        """处理撤回消息"""
        if not self.enable:
            return True
        
        # 获取撤回的消息信息
        revoke_info = message.get("Revoke", {})
        new_msg_id = revoke_info.get("NewMsgId", 0)  # 用于查找被撤回的消息
        from_wxid = message.get("FromWxid", "")
        
        if not new_msg_id or not from_wxid:
            return True
        
        # 获取聊天会话
        if from_wxid not in self.chat_sessions:
            return True
        
        session = self.chat_sessions[from_wxid]
        
        # 查找被撤回的消息
        revoked_msg = session.find_message_by_new_msg_id(new_msg_id)
        
        # 如果找到被撤回的消息并且该消息被机器人复读过
        if revoked_msg and (content := revoked_msg.get("content", "")) and (msg_info := session.get_repeated_msg_info(content)):
            try:
                logger.info("🤖 [Repeater] 准备撤回复读消息: {}", content)
                
                result = await bot.revoke_message(
                    from_wxid,
                    msg_info["msg_id"],
                    msg_info["create_time"],
                    msg_info["new_msg_id"]
                )
                
                if result:
                    logger.success("🤖 [Repeater] \x1b[32m撤回复读消息成功\x1b[0m")
                else:
                    logger.error("🤖 [Repeater] \x1b[31m撤回复读消息失败\x1b[0m")
            except Exception as e:
                logger.error("🤖 [Repeater] \x1b[31m撤回复读消息失败: {}\x1b[0m", str(e))
        
        return True
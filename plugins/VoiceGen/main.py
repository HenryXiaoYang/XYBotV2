import os
import time
import asyncio
import tomllib
import tempfile
import subprocess
from loguru import logger

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase


class VoiceGen(PluginBase):
    description = "语音生成插件"
    author = "Assistant"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        # 获取配置文件路径
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        
        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)
                
            # 读取基本配置
            basic_config = config.get("basic", {})
            self.enable = basic_config.get("enable", False)  # 读取插件开关

            # 读取语音配置
            voice_config = config.get("voice", {})
            self.allowed_wxids = voice_config.get("allowed_wxids", [])  # 允许使用的wxid列表
            
            # 读取昵称映射
            self.nickname_mapping = voice_config.get("nickname_mapping", {})
            # 创建反向映射（wxid到昵称）
            self.reverse_mapping = {v: k for k, v in self.nickname_mapping.items()}
            
            # 读取音色配置
            self.voices = voice_config.get("voices", {})
            # 设置默认音色配置
            default_voice = self.voices.get("default", {})
            self.ref_audio = default_voice.get("ref_audio", "./ref_audio.wav")
            self.ref_text = default_voice.get("ref_text", "This is ref text.")
            self.cross_fade_duration = voice_config.get("cross_fade_duration", 0.3)

            logger.info("🎯 [VoiceGen] \x1b[32m加载配置成功\x1b[0m")

        except Exception as e:
            logger.error("🎯 [VoiceGen] \x1b[31m加载配置失败: {}\x1b[0m", str(e))
            self.enable = False  # 如果加载失败，禁用插件

    async def async_init(self):
        return

    def get_nickname(self, wxid: str) -> str:
        """获取wxid对应的昵称，如果没有映射关系则返回原wxid"""
        return self.reverse_mapping.get(wxid, wxid)

    def get_wxid(self, nickname: str) -> str:
        """获取昵称对应的wxid，如果没有映射关系则返回原昵称"""
        return self.nickname_mapping.get(nickname, nickname)

    def _run_tts_command(self, cmd: list, output_path: str) -> bytes:
        """在单独的线程中执行TTS命令并读取生成的文件
        
        Args:
            cmd (list): 要执行的命令
            output_path (str): 输出文件路径
            
        Returns:
            bytes: 生成的语音数据
            
        Raises:
            subprocess.CalledProcessError: 命令执行失败
            FileNotFoundError: 输出文件不存在
            IOError: 文件读取失败
        """
        # 执行命令
        subprocess.run(cmd, check=True)
        
        # 读取生成的文件
        with open(output_path, "rb") as f:
            return f.read()

    async def generate_voice(self, gen_text: str, voice_name: str = "默认") -> bytes:
        """异步生成语音数据
        
        Args:
            gen_text (str): 要转换为语音的文本
            voice_name (str): 音色名称，默认使用"默认"音色
            
        Returns:
            bytes: 生成的语音数据
            
        Raises:
            ValueError: 音色不存在
            subprocess.CalledProcessError: 命令执行失败
            FileNotFoundError: 输出文件不存在
            IOError: 文件读取失败
        """
        # 检查音色是否存在
        if voice_name not in self.voices:
            raise ValueError(f"音色 {voice_name} 不存在")
            
        voice_config = self.voices[voice_name]
        ref_audio = voice_config["ref_audio"]
        ref_text = voice_config["ref_text"]
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 生成随机文件名
            output_file = "output.wav"
            output_path = os.path.join(temp_dir, output_file)
            
            logger.debug("🎯 [VoiceGen] 临时输出路径: {}", output_path)
            
            # 构建命令
            cmd = [
                "conda",
                "run",
                "-n",
                "f5-tts",
                "f5-tts_infer-cli",
                "--model", "F5-TTS",
                "--ref_audio", ref_audio,
                "--ref_text", ref_text,
                "--gen_text", gen_text,
                "--cross_fade_duration", str(self.cross_fade_duration),
                "--output_dir", temp_dir,
                "--output_file", output_file
            ]
            
            # 执行命令
            logger.debug("🎯 [VoiceGen] 执行命令: {}", " ".join(cmd))
            
            # 在单独的线程中执行命令
            return await asyncio.to_thread(self._run_tts_command, cmd, output_path)

    @on_text_message(priority=50)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        """处理文本消息
        
        Args:
            bot (WechatAPIClient): 机器人API客户端
            message (dict): 消息数据
        
        Returns:
            bool: 是否继续处理其他插件
        """
        if not self.enable:
            logger.info("🎯 [VoiceGen] \x1b[33m插件未启用\x1b[0m")
            return True

        # 检查发送者是否有权限
        sender_wxid = message["SenderWxid"]
        if sender_wxid not in self.allowed_wxids:
            return True

        # 解析命令
        content = message["Content"].strip()
        from_wxid = message["FromWxid"]
        is_private = not message["IsGroup"]  # 判断是否为私聊

        # 处理私聊的音色命令
        if is_private and "说" in content:
            parts = content.split("说", 1)
            if len(parts) != 2:
                return True
                
            voice_name = parts[0].strip()
            gen_text = parts[1].strip()
            
            if not voice_name or not gen_text:
                return True
                
            if voice_name not in self.voices:
                # await bot.send_text_message(from_wxid, f"音色 {voice_name} 不存在")
                logger.info("🎯 [VoiceGen] \x1b[33m发送失败 -> 音色不存在\x1b[0m")
                return True
                
            try:
                start_time = time.time()
                logger.info("🎯 [VoiceGen] 开始使用音色 \x1b[33m{}\x1b[0m 生成语音...", voice_name)
                voice_bytes = await self.generate_voice(gen_text, voice_name)
                logger.success("🎯 [VoiceGen] \x1b[32m语音生成成功\x1b[0m")
                
                await bot.send_voice_message(from_wxid, voice_bytes, format='wav')
                
                elapsed_time = time.time() - start_time
                success_msg = f"语音生成成功！用时{elapsed_time:.2f}秒。"
                # await bot.send_text_message(from_wxid, success_msg)
                logger.success("🎯 [VoiceGen] \x1b[32m{}\x1b[0m", success_msg)
                
            except Exception as e:
                error_msg = f"生成或发送语音失败: {str(e)}"
                logger.error("🎯 [VoiceGen] \x1b[31m{}\x1b[0m", error_msg)
                # await bot.send_text_message(from_wxid, error_msg)
                raise
                
            return False

        # 处理原有的语音命令（支持群聊和私聊）
        parts = content.split(" ", 2)  # 最多分割2次，保留最后的文本完整性
        if len(parts) != 3 or parts[0] != "语音":
            return True

        sender_name = self.get_nickname(sender_wxid)
        logger.info("🎯 [VoiceGen] 收到来自 \x1b[33m{}\x1b[0m 的消息", sender_name)
            
        target_nickname = parts[1]
        target_wxid = self.get_wxid(target_nickname)
        gen_text = parts[2]
        
        if not target_wxid:
            error_msg = f"未找到昵称 {target_nickname} 对应的wxid"
            await bot.send_text_message(from_wxid, error_msg)
            logger.info("🎯 [VoiceGen] \x1b[33m发送失败 -> 未找到昵称\x1b[0m")
            return False
        
        logger.info("🎯 [VoiceGen] 准备为 \x1b[33m{}\x1b[0m 生成语音", target_nickname)
        logger.debug("🎯 [VoiceGen] 生成文本: {}", gen_text)
        
        try:
            start_time = time.time()
            # 生成语音
            logger.info("🎯 [VoiceGen] 开始生成语音...")
            voice_bytes = await self.generate_voice(gen_text)
            logger.success("🎯 [VoiceGen] \x1b[32m语音生成成功\x1b[0m")
            
            # 发送语音
            logger.info("🎯 [VoiceGen] 正在发送语音给 \x1b[33m{}\x1b[0m...", target_nickname)
            await bot.send_voice_message(target_wxid, voice_bytes, format='wav')
            
            # 计算用时并发送成功消息
            elapsed_time = time.time() - start_time
            success_msg = f"已向{target_nickname}发送语音成功！用时{elapsed_time:.2f}秒。"
            await bot.send_text_message(from_wxid, success_msg)
            logger.success("🎯 [VoiceGen] \x1b[32m{}\x1b[0m", success_msg)
            
        except Exception as e:
            error_msg = f"生成或发送语音失败: {str(e)}"
            logger.error("🎯 [VoiceGen] \x1b[31m{}\x1b[0m", error_msg)
            await bot.send_text_message(from_wxid, error_msg)
            raise
            
        return False 
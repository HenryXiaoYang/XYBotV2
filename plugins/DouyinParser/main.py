import re
import tomllib
import os
from typing import Dict, Any
import traceback
import asyncio

import aiohttp
from loguru import logger

from WechatAPI import WechatAPIClient
from utils.decorators import on_text_message
from utils.plugin_base import PluginBase


class DouyinParserError(Exception):
    """抖音解析器自定义异常基类"""
    pass


class DouyinParser(PluginBase):
    description = "抖音无水印解析插件"
    author = "姜不吃先生"  # 群友太给力了！
    version = "1.0.2"

    def __init__(self):
        super().__init__()
        self.url_pattern = re.compile(r'https?://v\.douyin\.com/\w+/?')

        # 读取代理配置
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)
                
            # 基础配置
            basic_config = config.get("basic", {})
            self.enable = basic_config.get("enable", True)
            self.http_proxy = basic_config.get("http_proxy", None)
            
        except Exception as e:
            logger.error(f"加载抖音解析器配置文件失败: {str(e)}")
            self.enable = True
            self.http_proxy = None

        logger.debug("[抖音] 插件初始化完成，代理设置: {}", self.http_proxy)

    def _clean_response_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清理响应数据"""
        if not data:
            return data

        # 使用固定的抖音图标作为封面
        data[
            'cover'] = "https://is1-ssl.mzstatic.com/image/thumb/Purple221/v4/7c/49/e1/7c49e1af-ce92-d1c4-9a93-0a316e47ba94/AppIcon_TikTok-0-0-1x_U007epad-0-1-0-0-85-220.png/512x512bb.jpg"

        return data

    def _clean_url(self, url: str) -> str:
        """清理URL中的特殊字符"""
        cleaned_url = url.strip().replace(';', '').replace('\n', '').replace('\r', '')
        logger.debug("[抖音] 清理后的URL: {}", cleaned_url)  # 添加日志
        return cleaned_url

    async def _get_real_video_url(self, video_url: str) -> str:
        """获取真实视频链接"""
        max_retries = 3  # 最大重试次数
        retry_delay = 2  # 重试延迟秒数
        
        for retry in range(max_retries):
            try:
                logger.info("[抖音] 开始获取真实视频链接: {} (第{}次尝试)", video_url, retry + 1)
                
                # 修正代理格式
                proxy = f"http://{self.http_proxy}" if self.http_proxy and not self.http_proxy.startswith(('http://', 'https://')) else self.http_proxy
                logger.debug("[抖音] 使用代理: {}", proxy)
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Range': 'bytes=0-'
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(video_url, 
                                         proxy=proxy, 
                                         headers=headers,
                                         allow_redirects=True, 
                                         timeout=60) as response:  # 延长超时时间到60秒
                        if response.status == 200 or response.status == 206:
                            # 获取所有重定向历史
                            history = [str(resp.url) for resp in response.history]
                            real_url = str(response.url)
                            
                            # 记录重定向链接历史，用于调试
                            if history:
                                logger.debug("[抖音] 重定向历史: {}", history)
                            
                            # 检查是否获取到了真实的视频URL
                            if real_url != video_url and ('v3-' in real_url.lower() or 'douyinvod.com' in real_url.lower()):
                                logger.info("[抖音] 成功获取真实链接: {}", real_url)
                                return real_url
                            else:
                                logger.warning("[抖音] 未能获取到真实视频链接，准备重试")
                                if retry < max_retries - 1:  # 如果不是最后一次尝试，则等待后重试
                                    await asyncio.sleep(retry_delay)
                                    continue
                                return video_url
                        else:
                            logger.error("[抖音] 获取视频真实链接失败, 状态码: {}", response.status)
                            logger.debug("[抖音] 响应头: {}", response.headers)
                            if retry < max_retries - 1:
                                await asyncio.sleep(retry_delay)
                                continue
                            return video_url
                        
            except Exception as e:
                logger.error("[抖音] 获取真实链接失败: {} (第{}次尝试)", str(e), retry + 1)
                if retry < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                return video_url
        
        logger.error("[抖音] 获取真实链接失败，已达到最大重试次数")
        return video_url

    async def _parse_douyin(self, url: str) -> Dict[str, Any]:
        """调用抖音解析API"""
        try:
            api_url = "https://apih.kfcgw50.me/api/douyin"
            clean_url = self._clean_url(url)
            params = {
                'url': clean_url,
                'type': 'json'
            }

            logger.debug("[抖音] 请求API: {}, 参数: {}", api_url, repr(params))  # 添加日志

            async with aiohttp.ClientSession() as session:
                # 使用代理
                proxy = f"http://{self.http_proxy}" if self.http_proxy and not self.http_proxy.startswith(('http://', 'https://')) else self.http_proxy
                async with session.get(api_url, params=params, timeout=30, proxy=proxy) as response:  # 使用代理
                    if response.status != 200:
                        raise DouyinParserError(f"API请求失败，状态码: {response.status}")

                    data = await response.json()
                    logger.debug("[抖音] API响应数据: {}", data)  # 添加日志

                    if data.get("code") == 200:
                        result = data.get("data", {})
                        if not result:
                            raise DouyinParserError("API返回数据为空")

                        # 获取真实视频链接
                        if result.get('video'):
                            result['video'] = await self._get_real_video_url(result['video'])

                        result = self._clean_response_data(result)
                        logger.debug("[抖音] 清理后的数据: {}", result)
                        return result
                    else:
                        raise DouyinParserError(data.get("message", "未知错误"))

        except (aiohttp.ClientTimeout, aiohttp.ClientError) as e:
            logger.error("[抖音] 解析失败: {}", str(e))
            raise DouyinParserError(str(e))
        except Exception as e:
            logger.error("[抖音] 解析过程发生未知错误: {}\n{}", str(e), traceback.format_exc())
            raise DouyinParserError(f"未知错误: {str(e)}")

    async def _send_test_card(self, bot: WechatAPIClient, chat_id: str, sender: str):
        """发送测试卡片消息"""
        try:
            # 测试数据
            test_data = {
                'video': 'https://v11-cold.douyinvod.com/c183ceff049f008265680819dbd8ac0a/67b206c0/video/tos/cn/tos-cn-ve-15/ok8JumeiqAI3pJ2nAiQE9rBiTfm1KtADABlBgV/?a=1128&ch=0&cr=0&dr=0&cd=0%7C0%7C0%7C0&cv=1&br=532&bt=532&cs=0&ds=3&ft=H4NIyvvBQx9Uf8ym8Z.6TQjSYE7OYMDtGkd~P4Aq8_45a&mime_type=video_mp4&qs=0&rc=ZzU5NTRnNDw1aGc5aDloZkBpanE4M3Y5cjNkeDMzNGkzM0AuLy1fLWFhXjQxNjFgYzRiYSNmXzZlMmRjcmdgLS1kLTBzcw%3D%3D&btag=80010e000ad000&cquery=100y&dy_q=1739716635&feature_id=aa7df520beeae8e397df15f38df0454c&l=20250216223715047FF68C05B9F67E1F19',
                'title': '测试视频标题',
                'name': '测试作者',
                'cover': 'https://is1-ssl.mzstatic.com/image/thumb/Purple221/v4/7c/49/e1/7c49e1af-ce92-d1c4-9a93-0a316e47ba94/AppIcon_TikTok-0-0-1x_U007epad-0-1-0-0-85-220.png/512x512bb.jpg'
            }

            logger.info("开始发送测试卡片")
            logger.debug(f"测试数据: {test_data}")

            # 发送测试卡片
            await bot.send_link_message(
                wxid=chat_id,
                url=test_data['video'],
                title=f"{test_data['title'][:30]} - {test_data['name'][:10]}",
                description="这是一个测试卡片消息",
                thumb_url=test_data['cover']
            )

            logger.info("测试卡片发送成功")

            # 发送详细信息
            debug_msg = (
                "🔍 测试卡片详情:\n"
                f"视频链接: {test_data['video']}\n"
                f"封面链接: {test_data['cover']}\n"
                f"标题: {test_data['title']} - {test_data['name']}"
            )
            await bot.send_text_message(
                wxid=chat_id,
                content=debug_msg,
                at=[sender]
            )

        except Exception as e:
            error_msg = f"测试卡片发送失败: {str(e)}"
            logger.error(error_msg)
            await bot.send_text_message(
                wxid=chat_id,
                content=error_msg,
                at=[sender]
            )

    @on_text_message(priority=80)
    async def handle_douyin_links(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return True

        content = message['Content']
        sender = message['SenderWxid']
        chat_id = message['FromWxid']

        # 添加测试命令识别
        if content.strip() == "测试卡片":
            await self._send_test_card(bot, chat_id, sender)
            return

        try:
            # 提取抖音链接并清理
            match = self.url_pattern.search(content)
            if not match:
                return

            original_url = self._clean_url(match.group(0))
            logger.info(f"发现抖音链接: {original_url}")
            
            # 添加解析提示
            msg_args = {
                'wxid': chat_id,
                'content': "检测到抖音分享链接，正在解析无水印视频...\n" if message['IsGroup'] else "检测到抖音分享链接，正在解析无水印视频..."
            }
            if message['IsGroup']:
                msg_args['at'] = [sender]
            await bot.send_text_message(**msg_args)

            # 解析视频信息
            video_info = await self._parse_douyin(original_url)

            if not video_info:
                raise DouyinParserError("无法获取视频信息")

            # 获取视频信息
            video_url = video_info.get('video', '')
            title = video_info.get('title', '无标题')
            author = video_info.get('name', '未知作者')
            cover = video_info.get('cover', '')

            if not video_url:
                raise DouyinParserError("无法获取视频地址")

            # 发送文字版消息
            text_msg = (
                f"🎬 解析成功，微信内可直接观看（需ipv6）,浏览器打开可下载保存。\n"
                f"链接含有有效期，请尽快保存。\n"
            )
            if message['IsGroup']:
                text_msg = text_msg + "\n"
                await bot.send_text_message(wxid=chat_id, content=text_msg, at=[sender])
            else:
                await bot.send_text_message(wxid=chat_id, content=text_msg)

            # 发送卡片版消息
            await bot.send_link_message(
                wxid=chat_id,
                url=video_url,
                title=f"{title[:30]} - {author[:10]}" if author else title[:40],
                description="点击观看无水印视频",
                thumb_url=cover
            )

            logger.info(f"已发送解析结果: 标题[{title}] 作者[{author}]")

        except DouyinParserError as e:
            error_msg = str(e) if str(e) else "解析失败"
            logger.error(f"抖音解析失败: {error_msg}")
            if message['IsGroup']:
                await bot.send_text_message(wxid=chat_id, content=f"视频解析失败: {error_msg}\n", at=[sender])
            else:
                await bot.send_text_message(wxid=chat_id, content=f"视频解析失败: {error_msg}")
        except Exception as e:
            error_msg = str(e) if str(e) else "未知错误"
            logger.error(f"抖音解析发生未知错误: {error_msg}")
            if message['IsGroup']:
                await bot.send_text_message(wxid=chat_id, content=f"视频解析失败: {error_msg}\n", at=[sender])
            else:
                await bot.send_text_message(wxid=chat_id, content=f"视频解析失败: {error_msg}")

    async def async_init(self):
        """异步初始化函数"""
        # 可以在这里进行一些异步的初始化操作
        # 比如测试API可用性等
        pass

from loguru import logger

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase


class ExamplePlugin(PluginBase):
    description = "示例插件"
    author = "HenryXiaoYang"
    version = "1.0.0"

    # 同步初始化
    def __init__(self):
        super().__init__()

    # 异步初始化
    async def async_init(self):
        return

    @on_text_message(priority=99)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        logger.info("收到了文本消息。")

    @on_at_message(priority=50)
    async def handle_at(self, bot: WechatAPIClient, message: dict):
        logger.info("收到了被@消息，中等优先级")

    @on_voice_message()
    async def handle_voice(self, bot: WechatAPIClient, message: dict):
        logger.info("收到了语音消息，最低优先级")

    @on_image_message
    async def handle_image(self, bot: WechatAPIClient, message: dict):
        logger.info("收到了图片消息")

    @on_video_message
    async def handle_video(self, bot: WechatAPIClient, message: dict):
        logger.info("收到了视频消息")

    @on_file_message
    async def handle_file(self, bot: WechatAPIClient, message: dict):
        logger.info("收到了文件消息")

    @on_quote_message
    async def handle_quote(self, bot: WechatAPIClient, message: dict):
        logger.info("收到了引用消息")

    @on_pat_message
    async def handle_pat(self, bot: WechatAPIClient, message: dict):
        logger.info("收到了拍一拍消息")

    @on_emoji_message
    async def handle_emoji(self, bot: WechatAPIClient, message: dict):
        logger.info("收到了表情消息")

    @schedule('interval', seconds=5)
    async def periodic_task(self, bot: WechatAPIClient):
        logger.info("我每5秒执行一次")

    @schedule('cron', hour=8, minute=30, second=30)
    async def daily_task(self, bot: WechatAPIClient):
        logger.info("我每天早上8点30分30秒执行")

    @schedule('date', run_date='2025-01-29 00:00:00')
    async def new_year_task(self, bot: WechatAPIClient):
        logger.info("我在2025年1月29日执行")

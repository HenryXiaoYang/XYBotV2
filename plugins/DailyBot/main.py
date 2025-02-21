import tomllib
import requests
import os
import aiohttp
import re
from typing import Optional, Union
from urllib.parse import urlparse
from datetime import datetime, timedelta
import traceback  # 用于获取详细的异常堆栈信息
import asyncio
import random
import json

from loguru import logger
from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase

BASE_URL_VVHAN = "https://api.vvhan.com/api/"
BASE_URL_ALAPI = "https://v3.alapi.cn/api/"

class DailyBot(PluginBase):
    description = "日常生活服务助手"
    author = "koko"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        # 获取配置文件路径
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        
        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)
                
            # 基础配置
            basic_config = config.get("basic", {})
            self.enable = basic_config.get("enable", False)
            self.alapi_token = basic_config.get("alapi_token", None)

            # 通用配置
            common_config = config.get("common", {})
            self.user_agents = common_config.get("user_agents", [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            ])

            # 早报配置
            morning_news_config = config.get("morning_news", {})
            self.morning_news_text_enabled = morning_news_config.get("text_enabled", False)
            self.morning_news_command = morning_news_config.get("command", "早报")

            # 摸鱼日历配置
            moyu_config = config.get("moyu_calendar", {})
            self.moyu_backup_api = moyu_config.get("backup_api", "https://dayu.qqsuu.cn/moyuribao/apis.php")
            self.moyu_command = moyu_config.get("command", "摸鱼")

            # 八卦配置
            bagua_config = config.get("bagua", {})
            self.bagua_api_url = bagua_config.get("api_url", "https://dayu.qqsuu.cn/mingxingbagua/apis.php")
            self.bagua_command = bagua_config.get("command", "八卦")

            # KFC文案配置
            kfc_config = config.get("kfc", {})
            self.kfc_api_url = kfc_config.get("api_url", "https://api.suyanw.cn/api/kfcyl.php")
            self.kfc_command = kfc_config.get("command", "kfc")

            # 吃什么配置
            eat_config = config.get("eat", {})
            self.eat_api_url = eat_config.get("api_url", "https://zj.v.api.aa1.cn/api/eats/")
            self.eat_command = eat_config.get("command", "吃什么")
            self.eat_aliases = eat_config.get("aliases", [
                "今天吃什么", "吃点什么", "中午吃什么", "中午吃啥",
                "晚上吃啥", "晚上吃什么", "吃啥", "吃啥?", "今天吃啥"
            ])

            # 星座运势配置
            horoscope_config = config.get("horoscope", {})
            self.horoscope_default_period = horoscope_config.get("default_period", "today")
            # 解析JSON字符串格式的zodiac_mapping
            zodiac_mapping_str = horoscope_config.get("zodiac_mapping", "{}")
            try:
                self.zodiac_mapping = json.loads(zodiac_mapping_str)
            except:
                self.zodiac_mapping = {
                    '白羊座': 'aries',
                    '金牛座': 'taurus',
                    '双子座': 'gemini',
                    '巨蟹座': 'cancer',
                    '狮子座': 'leo',
                    '处女座': 'virgo',
                    '天秤座': 'libra',
                    '天蝎座': 'scorpio',
                    '射手座': 'sagittarius',
                    '摩羯座': 'capricorn',
                    '水瓶座': 'aquarius',
                    '双鱼座': 'pisces'
                }

            # 快递查询配置
            express_config = config.get("express", {})
            self.express_default_order = express_config.get("default_order", "asc")

            # 天气查询配置
            weather_config = config.get("weather", {})
            self.weather_show_clothing_index = weather_config.get("show_clothing_index", True)
            self.weather_forecast_hours = weather_config.get("forecast_hours", 10)
            self.weather_default_city = weather_config.get("default_city", "北京")
            self.weather_tip_format = weather_config.get("tip_format", 
                "输入不规范，请输<国内城市+(今天|明天|后天|七天|7天)+天气>，比如 '广州天气'")
            self.weather_time_keywords = weather_config.get("time_keywords", 
                ["今天", "明天", "后天", "七天", "7天"])

            # 添加抽签配置
            chouqian_config = config.get("chouqian", {})
            self.chouqian_enabled = chouqian_config.get("enable", False)
            self.chouqian_command = chouqian_config.get("command", ["抽签"])
            self.chouqian_api_key = chouqian_config.get("api_key", "mzCDYZFp5w9rp8N42cwQM3qiZG")

        except Exception as e:
            logger.error(f"加载DailyBot插件配置文件失败: {str(e)}")
            self.enable = False
            self.alapi_token = None
            self.morning_news_text_enabled = False
            self.user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            ]
            # 设置其他配置项的默认值
            self.moyu_backup_api = "https://dayu.qqsuu.cn/moyuribao/apis.php"
            self.bagua_api_url = "https://dayu.qqsuu.cn/mingxingbagua/apis.php"
            self.kfc_api_url = "https://api.suyanw.cn/api/kfcyl.php"
            self.eat_api_url = "https://zj.v.api.aa1.cn/api/eats/"
            self.horoscope_default_period = "today"
            self.express_default_order = "asc"
            self.weather_show_clothing_index = True
            self.weather_forecast_hours = 10
            self.weather_default_city = "北京"
            self.weather_tip_format = "输入不规范，请输<国内城市+(今天|明天|后天|七天|7天)+天气>，比如 '广州天气'"
            self.weather_time_keywords = ["今天", "明天", "后天", "七天", "7天"]
            self.morning_news_command = "早报"
            self.moyu_command = "摸鱼"
            self.bagua_command = "八卦"
            self.kfc_command = "kfc"
            self.chouqian_enabled = False
            self.chouqian_command = ["抽签"]
            self.chouqian_api_key = "mzCDYZFp5w9rp8N42cwQM3qiZG"

    async def async_init(self):
        """异步初始化函数"""
        try:
            logger.info("[初始化] DailyBot初始化完成")
        except Exception as e:
            logger.error(f"DailyBot异步初始化失败: {str(e)}")
            self.enable = False

    @on_text_message(priority=50)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return True  # 继续执行其他插件

        content = str(message["Content"]).strip()
        command = content.split(" ")

        try:
            result = None
            
            if content == self.morning_news_command:
                logger.info("[早报] 收到早报请求")
                result = await self.get_morning_news()
                
                # 如果返回的是图片URL，发送图片消息
                if self.is_valid_url(result):
                    logger.info("[早报] 获取到有效的图片URL: {}", result)
                    image_content = await self.download_image(result)
                    if image_content:
                        await bot.send_image_message(message["FromWxid"], image=image_content)
                        return False  # 阻止其他插件处理
                    result = "获取早报图片失败"

            elif content == self.moyu_command:
                result = await self.get_moyu_calendar()
                if self.is_valid_url(result):
                    image_content = await self.download_image(result)
                    if image_content:
                        await bot.send_image_message(message["FromWxid"], image=image_content)
                        return False  # 阻止其他插件处理

            elif content == self.bagua_command:
                result = await self.get_mx_bagua()
                if self.is_valid_url(result):
                    image_content = await self.download_image(result)
                    if image_content:
                        await bot.send_image_message(message["FromWxid"], image=image_content)
                        return False  # 阻止其他插件处理

            elif content == self.kfc_command:
                result = await self.get_kfc_text()

            elif content == self.eat_command or content in self.eat_aliases:
                result = await self.get_eat_text()

            # 星座运势查询
            elif (horoscope_match := re.match(r'^([\u4e00-\u9fa5]{2}座)$', content)) and content in self.zodiac_mapping:
                zodiac_english = self.zodiac_mapping[content]
                result = await self.get_horoscope(zodiac_english)

            # 快递查询
            elif content.startswith("快递"):
                tracking_number = content[2:].strip().replace('：', ':')
                result = await self.query_express_info(tracking_number)

            # 天气查询
            elif weather_match := re.match(r'^(?:(.{2,7}?)(?:市|县|区|镇)?|(\d{7,9}))(:?今天|明天|后天|7天|七天)?(?:的)?天气$', content):
                city_or_id = weather_match.group(1) or weather_match.group(2) or self.weather_default_city
                date = weather_match.group(3)
                result = await self.get_weather(city_or_id, date, content)
            elif content == "天气":
                result = self.weather_tip_format

            # 抽签
            elif self.chouqian_enabled and command[0] in self.chouqian_command:
                result = await self.get_chouqian()

            # 统一处理消息发送
            if result is not None:
                if message["IsGroup"]:
                    await bot.send_at_message(message["FromWxid"], result, [message["SenderWxid"]])
                else:
                    result = result.lstrip("\n")  # 私聊去掉开头的换行符
                    await bot.send_text_message(message["FromWxid"], result)

            return False  # 阻止其他插件处理

        except Exception as e:
            error_msg = f"处理失败: {str(e)}"
            logger.error(f"[处理异常] {error_msg}\n{traceback.format_exc()}")
            if message["IsGroup"]:
                await bot.send_at_message(message["FromWxid"], error_msg, [message["SenderWxid"]])
            else:
                await bot.send_text_message(message["FromWxid"], error_msg)

            return True  # 发生错误时继续执行其他插件

    async def get_morning_news(self) -> str:
        """获取早报信息"""
        url = "http://api.suxun.site/api/sixs"
        try:
            # 记录请求开始
            logger.info("[早报] 开始请求API: {}", url)
            
            # 根据配置决定是否使用JSON格式
            params = {"type": "json"} if self.morning_news_text_enabled else {}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'image' in content_type:
                        # 直接返回图片URL
                        logger.info("[早报] 获取到图片URL: {}", response.url)
                        return str(response.url)
                    
                    # 尝试解析JSON
                    try:
                        morning_news_info = await response.json()
                        if isinstance(morning_news_info, dict) and morning_news_info.get('code') == '200':
                            if self.morning_news_text_enabled:
                                # 文本格式
                                news_list = [news for news in morning_news_info["news"]]
                                formatted_news = (
                                    f"☕早安，打工人！\n"
                                    f"{morning_news_info['date']} 今日早报\n\n"
                                    f"{chr(10).join(news_list)}\n\n"
                                    f"{morning_news_info['weiyu']}"
                                )
                                logger.info("[早报] 成功获取文本格式早报")
                                return formatted_news
                            else:
                                # 图片格式
                                img_url = morning_news_info['image']
                                logger.info("[早报] 成功获取图片URL: {}", img_url)
                                return img_url
                    except:
                        logger.error("[早报] JSON解析失败")
                        
                    error_msg = '早报信息获取失败，请稍后再试'
                    logger.error("[早报] API请求失败")
                    return error_msg
            
        except Exception as e:
            logger.error("[早报] API请求异常: {}\n{}", str(e), traceback.format_exc())
            return "获取早报失败，请稍后再试"

    async def make_request(self, url: str, method: str = "GET", headers: Optional[dict] = None, 
                         params: Optional[dict] = None, data: Optional[str] = None) -> Union[dict, str]:
        """发送HTTP请求"""
        conn = aiohttp.TCPConnector(ssl=False)  # 忽略SSL验证
        async with aiohttp.ClientSession(connector=conn) as session:
            if method.upper() == "GET":
                async with session.get(url, headers=headers, params=params) as response:
                    content_type = response.headers.get('Content-Type', '')
                    
                    # 如果是图片，直接返回URL
                    if 'image' in content_type:
                        return str(response.url)
                        
                    try:
                        return await response.json()
                    except:
                        # 如果JSON解析失败，尝试手动解析
                        text = await response.text()
                        try:
                            return json.loads(text)
                        except:
                            # 如果还是失败，检查是否是图片内容
                            if content_type.startswith(('image/', 'application/octet-stream')):
                                return str(response.url)
                            raise ValueError(f"Failed to parse response as JSON: {text[:100]}")
                            
            elif method.upper() == "POST":
                async with session.post(url, headers=headers, data=data) as response:
                    content_type = response.headers.get('Content-Type', '')
                    
                    # 如果是图片，直接返回URL
                    if 'image' in content_type:
                        return str(response.url)
                        
                    try:
                        return await response.json()
                    except:
                        text = await response.text()
                        try:
                            return json.loads(text)
                        except:
                            # 如果还是失败，检查是否是图片内容
                            if content_type.startswith(('image/', 'application/octet-stream')):
                                return str(response.url)
                            raise ValueError(f"Failed to parse response as JSON: {text[:100]}")
            else:
                raise ValueError("Unsupported HTTP method")

    async def download_image(self, url: str) -> Optional[bytes]:
        """下载图片内容"""
        try:
            # 使用cache目录存储临时文件
            cache_dir = os.path.join("resources", "cache", "dailybot")
            os.makedirs(cache_dir, exist_ok=True)
            
            logger.info("[图片下载] 开始下载图片: {}", url)
            # 随机生成现代浏览器User-Agent
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1'
            ]
            
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Referer': 'https://api.vvhan.com/'  # 添加来源头
            }
            
            # 使用带重试的请求
            for _ in range(3):  # 最多重试3次
                response = requests.get(url, 
                                     headers=headers, 
                                     verify=False, 
                                     timeout=30,
                                     stream=True)  # 使用流式下载
                
                if response.status_code == 200:
                    content = response.content
                    # 简单验证图片内容
                    if len(content) > 1024 and content.startswith(b'\xff\xd8') or content.startswith(b'\x89PNG'):
                        logger.info("[图片下载] 下载成功，大小: {} bytes", len(content))
                        return content
                    logger.warning("[图片下载] 图片内容验证失败")
                
                # 等待指数退避
                await asyncio.sleep(2 ** _)
                
            logger.error("[图片下载] 多次重试失败")
            return None
            
        except Exception as e:
            logger.error(f"[图片下载] 下载异常: {str(e)}\n{traceback.format_exc()}")
            return None

    def is_valid_url(self, url: str) -> bool:
        """检查是否为有效的URL"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    async def get_moyu_calendar(self):
        """获取摸鱼人日历"""
        url = BASE_URL_VVHAN + "moyu?type=json"
        payload = "format=json"
        headers = {'Content-Type': "application/x-www-form-urlencoded"}
        try:
            moyu_calendar_info = await self.make_request(url, method="POST", headers=headers, data=payload)
            if isinstance(moyu_calendar_info, dict) and moyu_calendar_info['success']:
                return moyu_calendar_info['url']
            else:
                # 使用配置的备用API
                url = self.moyu_backup_api + "?type=json"
                payload = "format=json"
                headers = {'Content-Type': "application/x-www-form-urlencoded"}
                moyu_calendar_info = await self.make_request(url, method="POST", headers=headers, data=payload)
                if isinstance(moyu_calendar_info, dict) and moyu_calendar_info['code'] == 200:
                    moyu_pic_url = moyu_calendar_info['data']
                    if await self.is_valid_image_url(moyu_pic_url):
                        return moyu_pic_url
                    else:
                        return "周末无需摸鱼，愉快玩耍吧"
                else:
                    return "暂无可用"
        except Exception as e:
            logger.error(f"获取摸鱼日历失败: {str(e)}")
            return "获取摸鱼日历失败"

    async def get_mx_bagua(self):
        """获取明星八卦"""
        url = self.bagua_api_url
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    content_type = response.headers.get('Content-Type', '')
                    
                    # 如果是图片，直接返回URL
                    if 'image' in content_type:
                        logger.info("[八卦] 获取到图片URL: {}", response.url)
                        return str(response.url)
                    
                    # 尝试解析JSON
                    try:
                        bagua_info = await response.json()
                        if isinstance(bagua_info, dict) and bagua_info['code'] == 200:
                            bagua_pic_url = bagua_info["data"]
                            if await self.is_valid_image_url(bagua_pic_url):
                                return bagua_pic_url
                            else:
                                return "周末不更新，请微博吃瓜"
                    except:
                        logger.error("[八卦] JSON解析失败")
                        
                    return "暂无明星八卦，吃瓜莫急"
                    
        except Exception as e:
            logger.error(f"获取明星八卦失败: {str(e)}")
            return "获取明星八卦失败"

    async def get_kfc_text(self):
        """获取KFC文案"""
        url = self.kfc_api_url
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    content_type = response.headers.get('Content-Type', '')
                    
                    # 尝试解析JSON
                    try:
                        kfc_response = await response.json()
                        if isinstance(kfc_response, dict) and 'text' in kfc_response:
                            return kfc_response['text']
                    except:
                        # 如果JSON解析失败，尝试直接获取文本
                        try:
                            text = await response.text()
                            # 有些API直接返回文本而不是JSON
                            if text and len(text) > 10:  # 简单验证文本有效性
                                return text.strip()
                        except:
                            logger.error("[KFC] 文本解析失败")
                    
                    return "今天不想发文案 (╯°□°）╯︵ ┻━┻"
                    
        except Exception as e:
            logger.error(f"获取KFC文案失败: {str(e)}")
            return "获取KFC文案失败"

    async def get_eat_text(self):
        """获取吃什么建议"""
        url = self.eat_api_url
        try:
            logger.info("[吃什么] 开始请求API: {}", url)
            conn = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=conn) as session:
                async with session.get(url) as response:
                    content_type = response.headers.get('Content-Type', '')
                    logger.debug("[吃什么] 响应Content-Type: {}", content_type)
                    
                    # 获取响应文本
                    text = await response.text()
                    logger.debug("[吃什么] 响应内容: {}", text)
                    
                    # 尝试解析JSON，不管Content-Type
                    try:
                        eat_response = json.loads(text)
                        if isinstance(eat_response, dict):
                            meal1 = eat_response.get('meal1', '')
                            meal2 = eat_response.get('meal2', '')
                            mealwhat = eat_response.get('mealwhat', '')
                            if meal1 and meal2 and mealwhat:
                                result = f"A：吃{meal1}。\nB：吃{meal2}。\nC：{mealwhat}"
                                logger.info("[吃什么] 成功获取建议")
                                return result
                            logger.warning("[吃什么] 响应缺少必要字段")
                    except json.JSONDecodeError as e:
                        logger.warning("[吃什么] JSON解析失败: {}", str(e))
                        # 尝试从HTML中提取内容
                        if '<meal1>' in text and '<meal2>' in text:
                            import re
                            meal1 = re.search(r'<meal1>(.*?)</meal1>', text)
                            meal2 = re.search(r'<meal2>(.*?)</meal2>', text)
                            mealwhat = re.search(r'<mealwhat>(.*?)</mealwhat>', text)
                            if meal1 and meal2 and mealwhat:
                                result = f"A：吃{meal1.group(1)}。\nB：吃{meal2.group(1)}。\nC：{mealwhat.group(1)}"
                                logger.info("[吃什么] 成功获取HTML格式建议")
                                return result
                            logger.warning("[吃什么] HTML解析失败：未找到所有必要标签")
                    
                    return "今天吃什么呢？让我想想 🤔"
                    
        except Exception as e:
            logger.error("[吃什么] 请求异常: {}\n{}", str(e), traceback.format_exc())
            return "我也不知道吃啥啊？"

    async def get_horoscope(self, astro_sign: str, time_period: str = None):
        """获取星座运势"""
        if time_period is None:
            time_period = 'today'  # 默认使用today而不是配置值，因为API只支持固定值

        # 首先尝试使用 VVHAN API
        url = BASE_URL_VVHAN + "horoscope"
        params = {
            'type': astro_sign,
            'time': time_period  # 只能是 today/nextday/week/month
        }
        headers = {
            'Accept': 'application/json',
            'User-Agent': random.choice(self.user_agents)
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    try:
                        horoscope_data = await response.json()
                        if isinstance(horoscope_data, dict) and horoscope_data.get('success'):
                            data = horoscope_data['data']
                            result = (
                                f"{data['title']} ({data['time']}):\n\n"
                                f"💡【每日建议】\n宜：{data['todo']['yi']}\n忌：{data['todo']['ji']}\n\n"
                                f"📊【运势指数】\n"
                                f"总运势：{data['index']['all']}\n"
                                f"爱情：{data['index']['love']}\n"
                                f"工作：{data['index']['work']}\n"
                                f"财运：{data['index']['money']}\n"
                                f"健康：{data['index']['health']}\n\n"
                                f"🍀【幸运提示】\n数字：{data['luckynumber']}\n"
                                f"颜色：{data['luckycolor']}\n"
                                f"星座：{data['luckyconstellation']}\n\n"
                                f"✍【简评】\n{data['shortcomment']}\n\n"
                                f"📜【详细运势】\n"
                                f"总运：{data['fortunetext']['all']}\n"
                                f"爱情：{data['fortunetext']['love']}\n"
                                f"工作：{data['fortunetext']['work']}\n"
                                f"财运：{data['fortunetext']['money']}\n"
                                f"健康：{data['fortunetext']['health']}\n"
                            )
                            return result
                    except:
                        logger.error("[星座] VVHAN API JSON解析失败")
        except Exception as e:
            logger.error(f"[星座] VVHAN API请求失败: {str(e)}")

        # 如果VVHAN API失败且存在ALAPI token，尝试使用ALAPI作为备用
        if self.alapi_token:
            logger.info("[星座] 尝试使用ALAPI备用")
            url = BASE_URL_ALAPI + "star"
            payload = f"token={self.alapi_token}&star={astro_sign}"
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            try:
                horoscope_data = await self.make_request(url, method="POST", headers=headers, data=payload)
                if isinstance(horoscope_data, dict) and horoscope_data.get('code') == 200:
                    data = horoscope_data['data']['day']
                    result = (
                        f"📅 日期：{data['date']}\n\n"
                        f"💡【每日建议】\n宜：{data['yi']}\n忌：{data['ji']}\n\n"
                        f"📊【运势指数】\n"
                        f"总运势：{data['all']}\n"
                        f"爱情：{data['love']}\n"
                        f"工作：{data['work']}\n"
                        f"财运：{data['money']}\n"
                        f"健康：{data['health']}\n\n"
                        f"🔔【提醒】：{data['notice']}\n\n"
                        f"🍀【幸运提示】\n数字：{data['lucky_number']}\n"
                        f"颜色：{data['lucky_color']}\n"
                        f"星座：{data['lucky_star']}\n\n"
                        f"✍【简评】\n总运：{data['all_text']}\n"
                        f"爱情：{data['love_text']}\n"
                        f"工作：{data['work_text']}\n"
                        f"财运：{data['money_text']}\n"
                        f"健康：{data['health_text']}\n"
                    )
                    return result
            except Exception as e:
                logger.error(f"[星座] ALAPI请求失败: {str(e)}")

        return "获取星座运势失败，请稍后再试"

    async def query_express_info(self, tracking_number: str, com: str = "", order: str = None):
        """查询快递信息"""
        if not self.alapi_token:
            return "请先配置alapi的token"

        if order is None:
            order = self.express_default_order

        url = BASE_URL_ALAPI + "kd"
        payload = f"token={self.alapi_token}&number={tracking_number}&com={com}&order={order}"
        headers = {'Content-Type': "application/x-www-form-urlencoded"}

        try:
            response_json = await self.make_request(url, method="POST", headers=headers, data=payload)
            if not isinstance(response_json, dict) or response_json is None:
                return "查询失败：api响应为空"

            code = response_json.get("code", None)
            if code != 200:
                msg = response_json.get("msg", "未知错误")
                logger.error(f"快递查询失败: {msg}")
                return f"查询失败，{msg}"

            data = response_json.get("data", None)
            formatted_result = [
                f"快递编号：{data.get('nu')}",
                f"快递公司：{data.get('com')}",
                f"状态：{data.get('status_desc')}",
                "状态信息："
            ]
            for info in data.get("info"):
                time_str = info.get('time')[5:-3]
                formatted_result.append(f"{time_str} - {info.get('status_desc')}\n    {info.get('content')}")

            return "\n".join(formatted_result)
        except Exception as e:
            logger.error(f"快递查询失败: {str(e)}")
            return "快递查询失败"

    async def get_weather(self, city_or_id: str, date: str, content: str):
        """获取天气信息"""
        if not self.alapi_token:
            return "请先配置alapi的token"

        # 先验证输入格式
        if not city_or_id or city_or_id in ['明天', '后天', '七天', '7天']:
            return "输入不规范，请输<国内城市+(今天|明天|后天|七天|7天)+天气>，比如 '广州天气'"

        url = BASE_URL_ALAPI + 'tianqi'
        isFuture = date in ['明天', '后天', '七天', '7天']
        if isFuture:
            url = BASE_URL_ALAPI + 'tianqi/seven'

        try:
            logger.info("[天气] 开始查询: {} {}", city_or_id, date or "今天")
            params = {
                'token': self.alapi_token,
                'city': city_or_id if not city_or_id.isnumeric() else None,
                'city_id': city_or_id if city_or_id.isnumeric() else None
            }
            params = {k: v for k, v in params.items() if v is not None}  # 移除None值
            
            weather_data = await self.make_request(url, "GET", params=params)
            logger.debug("[天气] API响应: {}", weather_data)
            
            if isinstance(weather_data, dict) and weather_data.get('code') == 200:
                data = weather_data['data']
                
                # 验证城市名称匹配
                if not city_or_id.isnumeric() and data['city'] not in content:
                    return "输入不规范，请输<国内城市+(今天|明天|后天|七天|7天)+天气>，比如 '广州天气'"

                if isFuture:
                    formatted_output = []
                    for num, d in enumerate(data):
                        if num == 0:
                            formatted_output.append(f"🏙️ 城市: {d['city']} ({d['province']})\n")
                        if date == '明天' and num != 1:
                            continue
                        if date == '后天' and num != 2:
                            continue
                        basic_info = [
                            f"🕒 日期: {d['date']}",
                            f"🌦️ 天气: 🌞{d['wea_day']}| 🌛{d['wea_night']}",
                            f"🌡️ 温度: 🌞{d['temp_day']}℃| 🌛{d['temp_night']}℃",
                            f"🌅 日出/日落: {d['sunrise']} / {d['sunset']}",
                        ]
                        if 'index' in d and isinstance(d['index'], list):
                            for i in d['index']:
                                if isinstance(i, dict):
                                    basic_info.append(f"{i.get('name', '')}: {i.get('level', '')}")
                        formatted_output.append("\n".join(basic_info) + '\n')
                    return "\n".join(formatted_output)

                update_time = data['update_time']
                dt_object = datetime.strptime(update_time, "%Y-%m-%d %H:%M:%S")
                formatted_update_time = dt_object.strftime("%m-%d %H:%M")

                formatted_output = []
                basic_info = (
                    f"🏙️ 城市: {data['city']} ({data['province']})\n"
                    f"🕒 更新: {formatted_update_time}\n"
                    f"🌦️ 天气: {data['weather']}\n"
                    f"🌡️ 温度: ↓{data['min_temp']}℃| 现{data['temp']}℃| ↑{data['max_temp']}℃\n"
                    f"🌬️ 风向: {data['wind']}\n"
                    f"💦 湿度: {data['humidity']}\n"
                    f"🌅 日出/日落: {data['sunrise']} / {data['sunset']}\n"
                )
                formatted_output.append(basic_info)

                if self.weather_show_clothing_index:
                    if 'index' in data and isinstance(data['index'], dict):
                        chuangyi_data = data['index'].get('chuangyi', {})
                        if chuangyi_data:
                            chuangyi_level = chuangyi_data.get('level', '未知')
                            chuangyi_content = chuangyi_data.get('content', '未知')
                            chuangyi_info = f"👚 穿衣指数: {chuangyi_level} - {chuangyi_content}\n"
                            formatted_output.append(chuangyi_info)

                if 'hour' in data and isinstance(data['hour'], list):
                    ten_hours_later = dt_object + timedelta(hours=self.weather_forecast_hours)
                    future_weather = []
                    for hour_data in data['hour']:
                        forecast_time_str = hour_data.get('time', '')
                        if forecast_time_str:
                            forecast_time = datetime.strptime(forecast_time_str, "%Y-%m-%d %H:%M:%S")
                            if dt_object < forecast_time <= ten_hours_later:
                                future_weather.append(
                                    f"     {forecast_time.hour:02d}:00 - {hour_data.get('wea', '')} - {hour_data.get('temp', '')}°C"
                                )

                    if future_weather:
                        future_weather_info = f"⏳ 未来{self.weather_forecast_hours}小时的天气预报:\n" + "\n".join(future_weather)
                        formatted_output.append(future_weather_info)

                if 'alarm' in data and data['alarm']:
                    alarm_info = "⚠️ 预警信息:\n"
                    for alarm in data['alarm']:
                        if isinstance(alarm, dict):
                            alarm_info += (
                                f"🔴 标题: {alarm.get('title', '')}\n"
                                f"🟠 等级: {alarm.get('level', '')}\n"
                                f"🟡 类型: {alarm.get('type', '')}\n"
                                f"🟢 提示: \n{alarm.get('tips', '')}\n"
                                f"🔵 内容: \n{alarm.get('content', '')}\n\n"
                            )
                    formatted_output.append(alarm_info)

                return "\n".join(formatted_output)
            else:
                logger.error("[天气] API返回错误: {}", weather_data)
                return "获取天气信息失败，请稍后再试"
                
        except Exception as e:
            logger.error("[天气] 请求异常: {}\n{}", str(e), traceback.format_exc())
            return "获取天气信息失败"

    async def is_valid_image_url(self, url: str) -> bool:
        """检查是否为有效的图片URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"检查图片URL失败: {str(e)}")
            return False

    async def get_chouqian(self):
        """获取抽签结果"""
        url = "https://api.t1qq.com/api/tool/cq"
        params = {'key': self.chouqian_api_key}

        try:
            logger.info("[抽签] 开始请求API: {}", url)
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    logger.debug("[抽签] API响应: {}", data)

                    if data.get('code') == 200:
                        title = data.get('title', "未获取到签标题")
                        qian = data.get('qian', "未获取到签诗")
                        jie = data.get('jie', "未获取到解签")
                        logger.info("[抽签] 成功获取抽签结果: {}", title)
                        return f"\n🎯 {title}\n\n📝 签诗：\n{qian}\n\n📖 解签：\n{jie}"
                    else:
                        logger.warning("[抽签] API返回错误: {}", data)
                        return "抽签失败，请稍后再试"
        except Exception as e:
            logger.error("[抽签] 请求异常: {}\n{}", str(e), traceback.format_exc())
            return f"抽签出错：{str(e)}" 
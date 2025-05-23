import asyncio
import json
import os
import sys
import time
import tomllib
import traceback
from pathlib import Path

from loguru import logger

import WechatAPI
from WebUI.common.bot_bridge import bot_bridge
from WechatAPI.Server.WechatAPIServer import wechat_api_server
from database.XYBotDB import XYBotDB
from database.keyvalDB import KeyvalDB
from database.messsagDB import MessageDB
from utils.decorators import scheduler
from utils.plugin_manager import PluginManager
from utils.xybot import XYBot


async def run_bot():
    """
    机器人主要运行逻辑
    """

    try:
        # 设置工作目录
        script_dir = Path(__file__).resolve().parent

        # 读取主设置
        config_path = script_dir / "main_config.toml"
        with open(config_path, "rb") as f:
            main_config = tomllib.load(f)

        logger.success("读取主设置成功")

        # 启动WechatAPI服务
        server = wechat_api_server
        api_config = main_config.get("WechatAPIServer", {})
        redis_host = api_config.get("redis-host", "127.0.0.1")
        redis_port = api_config.get("redis-port", 6379)
        logger.debug("Redis 主机地址: {}:{}", redis_host, redis_port)
        await server.start(port=api_config.get("port", 9000),
                           mode=api_config.get("mode", "release"),
                           redis_host=redis_host,
                           redis_port=redis_port,
                           redis_password=api_config.get("redis-password", ""),
                           redis_db=api_config.get("redis-db", 0))

        # 实例化WechatAPI客户端
        bot = WechatAPI.WechatAPIClient("127.0.0.1", api_config.get("port", 9000))
        bot.ignore_protect = main_config.get("XYBot", {}).get("ignore-protection", False)

        # 等待WechatAPI服务启动
        time_out = 10
        while not await bot.is_running() and time_out > 0:
            logger.info("等待WechatAPI启动中")
            await asyncio.sleep(2)
            time_out -= 2

        if time_out <= 0:
            logger.error("WechatAPI服务启动超时")
            return

        if not await bot.check_database():
            logger.error("Redis连接失败，请检查Redis是否在运行中，Redis的配置")
            return

        logger.success("WechatAPI服务已启动")

        # 加载插件目录下的所有插件
        plugin_manager = PluginManager()
        plugin_manager.set_bot(bot)
        loaded_plugins = await plugin_manager.load_plugins(load_disabled=False)
        logger.success(f"已加载插件: {loaded_plugins}")

        # ==========登陆==========

        # 检查并创建robot_stat.json文件
        robot_stat_path = script_dir / "resource" / "robot_stat.json"
        if not os.path.exists(robot_stat_path):
            default_config = {
                "wxid": "",
                "device_name": "",
                "device_id": ""
            }
            os.makedirs(os.path.dirname(robot_stat_path), exist_ok=True)
            with open(robot_stat_path, "w") as f:
                json.dump(default_config, f)
            robot_stat = default_config
        else:
            with open(robot_stat_path, "r") as f:
                robot_stat = json.load(f)

        wxid = robot_stat.get("wxid", None)
        device_name = robot_stat.get("device_name", None)
        device_id = robot_stat.get("device_id", None)

        if not await bot.is_logged_in(wxid):
            while not await bot.is_logged_in(wxid):
                # 需要登录
                try:
                    if await bot.get_cached_info(wxid):
                        # 尝试唤醒登录
                        uuid = await bot.awaken_login(wxid)
                        logger.success("获取到登录uuid: {}", uuid)
                    else:
                        # 二维码登录
                        if not device_name:
                            device_name = bot.create_device_name()
                        if not device_id:
                            device_id = bot.create_device_id()
                        uuid, url, qr = await bot.get_qr_code(device_id=device_id, device_name=device_name)
                        logger.success("获取到登录uuid: {}", uuid)
                        logger.success("获取到登录二维码: {}", url)
                        bot_bridge.save_profile(avatar_url=url)
                        logger.info("\n" + qr)
                except:
                    # 二维码登录
                    if not device_name:
                        device_name = bot.create_device_name()
                    if not device_id:
                        device_id = bot.create_device_id()
                    uuid, url, qr = await bot.get_qr_code(device_id=device_id, device_name=device_name)
                    logger.success("获取到登录uuid: {}", uuid)
                    logger.success("获取到登录二维码: {}", url)
                    bot_bridge.save_profile(avatar_url=url)
                    logger.info("\n" + qr)

                while True:
                    stat, data = await bot.check_login_uuid(uuid, device_id=device_id)
                    if stat:
                        break
                    logger.info("等待登录中，过期倒计时：{}", data)
                    await asyncio.sleep(5)

            # 保存登录信息
            robot_stat["wxid"] = bot.wxid
            robot_stat["device_name"] = device_name
            robot_stat["device_id"] = device_id
            with open("resource/robot_stat.json", "w") as f:
                json.dump(robot_stat, f)

            # 获取登录账号信息
            bot.wxid = data.get("acctSectResp", {}).get("userName", "")
            bot.nickname = data.get("acctSectResp", {}).get("nickName", "")
            bot.alias = data.get("acctSectResp", {}).get("alias", "")
            bot.phone = data.get("acctSectResp", {}).get("bindMobile", "")

            logger.info("登录账号信息: wxid: {}  昵称: {}  微信号: {}  手机号: {}", bot.wxid, bot.nickname, bot.alias,
                        bot.phone)

            bot_bridge.save_profile(avatar_url=data.get("userInfoExt", {}).get("BigHeadImgUrl", ""),
                                    nickname=data.get("acctSectResp", {}).get("nickName", ""),
                                    wxid=data.get("acctSectResp", {}).get("userName", ""),
                                    alias=data.get("acctSectResp", {}).get("alias", ""))


        else:  # 已登录
            bot.wxid = wxid
            profile = await bot.get_profile()

            bot.nickname = profile.get("NickName", {}).get("string", "")
            bot.alias = profile.get("Alias", "")
            bot.phone = profile.get("BindMobile", {}).get("string", "")

            logger.info("登录账号信息: wxid: {}  昵称: {}  微信号: {}  手机号: {}", bot.wxid, bot.nickname, bot.alias,
                        bot.phone)

            bot_bridge.save_profile(nickname=profile.get("NickName", {}).get("string", ""),
                                    wxid=wxid,
                                    alias=profile.get("Alias", ""))

        logger.info("登录设备信息: device_name: {}  device_id: {}", device_name, device_id)

        logger.success("登录成功")

        # ========== 登录完毕 开始初始化 ========== #

        # 开启自动心跳
        try:
            success = await bot.start_auto_heartbeat()
            if success:
                logger.success("已开启自动心跳")
            else:
                logger.warning("开启自动心跳失败")
        except ValueError:
            logger.warning("自动心跳已在运行")
        except Exception as e:
            if "在运行" not in str(e):
                logger.warning("自动心跳已在运行")

        # 初始化机器人
        xybot = XYBot(bot)
        xybot.update_profile(bot.wxid, bot.nickname, bot.alias, bot.phone)

        # 启动调度器
        if scheduler.state == 0:
            scheduler.start()
        logger.success("定时任务已启动")

        # ========== 开始接受消息 ========== #

        # 开始接受消息说明机器人开始正常运行

        keyval_db = KeyvalDB()
        await keyval_db.set("start_time", str(int(time.time())))

        # 先接受堆积消息
        logger.info("处理堆积消息中")
        count = 0
        while True:
            data = await bot.sync_message()
            data = data.get("AddMsgs")
            if not data:
                if count > 2:
                    break
                else:
                    count += 1
                    continue

            logger.debug("接受到 {} 条消息", len(data))
            await asyncio.sleep(1)
        logger.success("处理堆积消息完毕")

        logger.success("开始处理消息")
        while True:
            try:
                data = await bot.sync_message()
            except Exception as e:
                logger.warning("获取新消息失败 {}", e)
                await asyncio.sleep(5)
                continue

            data = data.get("AddMsgs")
            if data:
                for message in data:
                    asyncio.create_task(xybot.process_message(message))
            await asyncio.sleep(0.5)

    except asyncio.CancelledError:
        await wechat_api_server.stop()
        logger.info("机器人关闭")
    except Exception as e:
        logger.error(f"机器人运行出错: {e}")
        logger.error(traceback.format_exc())


async def init_system():
    """系统初始化"""
    print(
        "░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░ ░▒▓██████▓▒░▒▓████████▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░  \n"
        "░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░          ░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░ \n"
        "░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░           ░▒▓█▓▒▒▓█▓▒░       ░▒▓█▓▒░ \n"
        " ░▒▓██████▓▒░ ░▒▓██████▓▒░░▒▓███████▓▒░░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░           ░▒▓█▓▒▒▓█▓▒░ ░▒▓██████▓▒░  \n"
        "░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░            ░▒▓█▓▓█▓▒░ ░▒▓█▓▒░        \n"
        "░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░            ░▒▓█▓▓█▓▒░ ░▒▓█▓▒░        \n"
        "░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░   ░▒▓███████▓▒░ ░▒▓██████▓▒░  ░▒▓█▓▒░             ░▒▓██▓▒░  ░▒▓████████▓▒░\n")

    # 配置日志
    logger.remove()

    logger.level("API", no=1, color="<cyan>")

    logger.add(
        "logs/xybot.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        encoding="utf-8",
        enqueue=True,
        rotation="10mb",
        retention="2 weeks",
        backtrace=True,
        diagnose=True,
        level="DEBUG",
    )
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
        level="TRACE",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )
    logger.add(
        "logs/wechatapi.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="API",
        encoding="utf-8",
        enqueue=True,
        rotation="10mb",
        retention="2 weeks",
        backtrace=True,
        diagnose=True,
        filter=lambda record: record["level"].name == "API",
    )

    # 初始化数据库
    XYBotDB()

    message_db = MessageDB()
    await message_db.initialize()

    keyval_db = KeyvalDB()
    await keyval_db.initialize()
    await keyval_db.delete("start_time")

    logger.success("数据库初始化成功")


async def main():
    """主入口函数"""
    await init_system()

    await run_bot()


if __name__ == "__main__":
    if sys.version_info.major != 3 and sys.version_info.minor != 11:
        print("请使用Python3.11")
        sys.exit(1)

    asyncio.run(main())

# 个人原因，停止维护。

# 🤖 XYBot V2

XYBot V2 是一个功能丰富的微信机器人框架,支持多种互动功能和游戏玩法。

# 免责声明

- 这个项目免费开源，不存在收费。
- 本工具仅供学习和技术研究使用，不得用于任何商业或非法行为。
- 本工具的作者不对本工具的安全性、完整性、可靠性、有效性、正确性或适用性做任何明示或暗示的保证，也不对本工具的使用或滥用造成的任何直接或间接的损失、责任、索赔、要求或诉讼承担任何责任。
- 本工具的作者保留随时修改、更新、删除或终止本工具的权利，无需事先通知或承担任何义务。
- 本工具的使用者应遵守相关法律法规，尊重微信的版权和隐私，不得侵犯微信或其他第三方的合法权益，不得从事任何违法或不道德的行为。
- 本工具的使用者在下载、安装、运行或使用本工具时，即表示已阅读并同意本免责声明。如有异议，请立即停止使用本工具，并删除所有相关文件。

# 📄 文档

## https://henryxiaoyang.github.io/XYBotV2

# ✨ 主要功能

## 🛠️ 基础功能

- 🤖 AI聊天 - 支持文字、图片、语音等多模态交互
- 📰 每日新闻 - 自动推送每日新闻
- 🎵 点歌系统 - 支持在线点歌
- 🌤️ 天气查询 - 查询全国各地天气
- 🎮 游戏功能 - 五子棋、战争雷霆玩家查询等

## 💎 积分系统

- 📝 每日签到 - 支持连续签到奖励
- 🎲 抽奖系统 - 多种抽奖玩法
- 🧧 红包系统 - 群内发积分红包
- 💰 积分交易 - 用户间积分转账
- 📊 积分排行 - 查看积分排名

## 👮 管理功能

- ⚙️ 插件管理 - 动态加载/卸载插件
- 👥 白名单管理 - 控制机器人使用权限
- 📊 积分管理 - 管理员可调整用户积分
- 🔄 签到重置 - 重置所有用户签到状态

# 🔌 插件系统

XYBot V2 采用插件化设计,所有功能都以插件形式实现。主要插件包括:

- 👨‍💼 AdminPoint - 积分管理
- 🔄 AdminSignInReset - 签到重置
- 🛡️ AdminWhitelist - 白名单管理
- 🤖 Ai - AI聊天
- 📊 BotStatus - 机器人状态
- 📱 GetContact - 获取通讯录
- 🌤️ GetWeather - 天气查询
- 🎮 Gomoku - 五子棋游戏
- 🌅 GoodMorning - 早安问候
- 📈 Leaderboard - 积分排行
- 🎲 LuckyDraw - 幸运抽奖
- 📋 Menu - 菜单系统
- 🎵 Music - 点歌系统
- 📰 News - 新闻推送
- 💱 PointTrade - 积分交易
- 💰 QueryPoint - 积分查询
- 🎯 RandomMember - 随机群成员
- 🖼️ RandomPicture - 随机图片
- 🧧 RedPacket - 红包系统
- ✍️ SignIn - 每日签到
- ✈️ Warthunder - 战争雷霆查询

# 🚀 部署说明

## 💻 Python部署

### 🪟 Windows部署

#### 1. 环境准备

- 安装 Python 3.11: https://www.python.org/downloads/release/python-3119/
- 安装 ffmpeg: 从[ffmpeg官网](https://www.ffmpeg.org/download.html)下载并添加到环境变量
- 安装 Redis: 从[Redis](https://github.com/tporadowski/redis/releases/tag/v5.0.14.1)下载并启动服务

#### 2. 安装项目

```bash
git clone https://github.com/HenryXiaoYang/XYBotV2.git
cd XYBotV2
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

#### 3. 启动机器人

```bash
start redis-server
python app.py
```

### 🐧 Linux部署

#### 1. 环境准备

```bash
sudo apt update
sudo apt install python3.11 python3.11-venv redis-server ffmpeg
sudo systemctl start redis
sudo systemctl enable redis
```

#### 2. 安装项目

```bash
git clone https://github.com/HenryXiaoYang/XYBotV2.git
cd XYBotV2
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. 启动机器人

```bash
python app.py
```

### 🌌 无WebUI简单启动

如果你不需要WebUI界面，可以直接使用bot.py：

```bash
python bot.py
```

## ⚙️ 配置说明

- 主配置: main_config.toml
- 插件配置: plugins/all_in_one_config.toml

这几个插件需要配置API密钥:
- 🤖 Ai
- 🌤️ GetWeather

## ❓ 常见问题

1. 与网络相关的报错
   - 检查网络连接
   - 关闭代理软件
   - 重启XYBot和Redis

2. `正在运行`相关的报错
   - 将占用9000端口的进程结束

3. 无法访问Web界面
   - 确保9999端口已开放
   - 配置防火墙允许9999端口

# 💻 代码提交

提交代码时请使用 `feat: something` 作为说明，支持的标识如下:

- `feat` 新功能(feature)
- `fix` 修复bug
- `docs` 文档(documentation)
- `style` 格式(不影响代码运行的变动)
- `ref` 重构(即不是新增功能，也不是修改bug的代码变动)
- `perf` 性能优化(performance)
- `test` 增加测试
- `chore` 构建过程或辅助工具的变动
- `revert` 撤销

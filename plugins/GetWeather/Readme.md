# 🌤️ 天气查询插件

## 📝 功能说明
本插件提供天气查询功能，支持多种查询格式：
- 天气 城市名
- 天气城市名
- 城市名天气
- 城市名 天气

## 🔑 配置说明

### 1. 获取和风天气 API Key
1. 访问[和风天气开发平台](https://dev.qweather.com/docs/configuration/project-and-key/)
2. 注册并创建应用
3. 获取 API Key

### 2. 生成密钥对
```bash
# 生成私钥
openssl genpkey -algorithm ED25519 -out ed25519-private.pem

# 从私钥生成公钥
openssl pkey -pubout -in ed25519-private.pem > ed25519-public.pem

cat ./ed25519-private.pem
```

### 3. 配置插件
1. 打开 `config.toml` 文件
2. 将私钥内容设置为 `api-key` 的值：
```toml
[GetWeather]
enable = true
api-key = "你的私钥内容"
```

## 🚀 使用方法
1. 在聊天中发送以下任意格式：
   - `天气 北京`
   - `天气北京`
   - `北京天气`
   - `北京 天气`

2. 机器人将返回该城市的天气信息，包括：
   - 实时天气
   - 温度
   - 湿度
   - 风向
   - 风力等级

## ⚠️ 注意事项
1. 确保 API Key 正确配置
2. 城市名称需要准确，建议使用标准城市名
3. 如遇到查询失败，请检查网络连接和 API Key 是否有效

## 🔧 故障排除
1. 如果插件无法响应，请检查：
   - 配置文件是否正确
   - API Key 是否有效
   - 网络连接是否正常

2. 如果返回错误信息，请确认：
   - 城市名称是否正确
   - API 调用次数是否超限
   - 服务器是否正常运行

## 📞 支持与反馈
如有问题或建议，请通过以下方式反馈：
1. 提交 Issue
2. 联系管理员
3. 在交流群中反馈


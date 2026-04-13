# AI 聊天系统

## 项目简介

AI 聊天系统是一个基于 Vue 3 + FastAPI 开发的智能对话系统，支持用户注册登录、个人信息管理、多轮对话和历史对话记录等功能。

## 技术栈

- **前端**：Vue 3 + Vite + JavaScript
- **后端**：FastAPI + Python
- **数据库**：MySQL
- **认证**：JWT Token
- **AI 接口**：DeepSeek API

## 功能特点

- ✅ 用户注册和登录
- ✅ 个人信息管理（修改用户名、邮箱、姓名、学号）
- ✅ 会话管理（创建新会话、切换会话）
- ✅ 多轮对话（基于 DeepSeek API）
- ✅ 历史对话记录
- ✅ 响应式设计
- ✅ 暗黑主题

## 项目结构

```
├── ai-chat-frontend/       # 前端代码
│   ├── src/                # 源代码
│   │   ├── views/          # 页面组件
│   │   ├── services/       # API 服务
│   │   ├── router/         # 路由配置
│   │   └── component/      # 通用组件
│   ├── index.html          # 入口 HTML
│   ├── package.json        # 依赖配置
│   └── vite.config.js      # Vite 配置
├── ai-chat-backend/        # 后端代码
│   ├── agents/             # AI 代理
│   ├── auth_models.py      # 认证模型
│   ├── auth_routes.py      # 认证路由
│   ├── auth_utils.py       # 认证工具
│   ├── database.py         # 数据库配置
│   ├── main.py             # 主入口
│   └── requirements.txt    # 依赖配置
└── ai_chat_interface.html  # 聊天界面设计参考
```

## 安装和运行

### 前端

1. 进入前端目录
   ```bash
   cd ai-chat-frontend
   ```

2. 安装依赖
   ```bash
   npm install
   ```

3. 启动开发服务器
   ```bash
   npm run dev
   ```

4. 访问地址：http://localhost:5173

### 后端

1. 进入后端目录
   ```bash
   cd ai-chat-backend
   ```

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

3. 配置环境变量（修改 .env 文件）
   ```
   # 数据库配置
   DATABASE_URL="mysql+aiomysql://username:password@localhost:3306/ai_chat_db"
   
   # JWT 密钥
   SECRET_KEY="your-secret-key-here"
   
   # DeepSeek API Key
   DEEPSEEK_API_KEY="your-deepseek-api-key"
   ```

4. 初始化数据库
   ```bash
   python init_db.py
   ```

5. 启动后端服务
   ```bash
   python main.py
   ```

6. 访问地址：http://localhost:8000

## API 文档

后端服务启动后，可以访问以下地址查看 API 文档：
- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

## 主要功能使用说明

### 1. 用户注册和登录
- 访问登录页面，点击"注册"按钮进入注册页面
- 填写注册信息，点击"注册"按钮完成注册
- 注册成功后，点击"登录"按钮返回登录页面
- 输入用户名和密码，点击"登录"按钮完成登录

### 2. 个人信息管理
- 登录后，点击左下角的修改个人信息按钮（✏️）
- 在弹出的修改个人信息弹窗中，修改个人信息
- 点击"保存修改"按钮完成修改

### 3. 会话管理
- 点击左侧边栏的"新对话"按钮创建新会话
- 点击左侧边栏的会话项切换会话
- 会话列表会自动保存历史对话记录

### 4. 多轮对话
- 在聊天输入框中输入问题，点击"发送"按钮
- 系统会调用 DeepSeek API 生成回复
- 可以继续输入新的问题，系统会根据历史对话记录生成上下文相关的回复

## 注意事项

1. 确保 MySQL 数据库已经安装并运行
2. 确保已经配置了正确的数据库连接信息
3. 确保已经获取了 DeepSeek API Key
4. 前端开发服务器和后端服务需要同时运行

## 故障排除

### 1. 数据库连接失败
- 检查数据库是否已经启动
- 检查数据库连接信息是否正确
- 检查数据库用户是否有足够的权限

### 2. 后端服务启动失败
- 检查依赖是否已经安装
- 检查环境变量是否已经配置
- 检查端口是否被占用

### 3. 前端无法连接到后端
- 检查后端服务是否已经启动
- 检查前端 API 服务配置是否正确
- 检查 CORS 配置是否允许前端访问

## 许可证

MIT License

## 联系方式

如有问题，请联系项目维护者。

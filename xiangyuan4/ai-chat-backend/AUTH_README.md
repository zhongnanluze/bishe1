# 登录模块使用说明

## 概述

本项目已集成完整的用户认证系统，支持用户注册、登录、Token管理、用户信息管理等功能。

## 技术栈

- **FastAPI** - Web框架
- **SQLAlchemy** - ORM框架
- **aiomysql** - 异步MySQL驱动
- **JWT (python-jose)** - Token认证
- **Passlib (bcrypt)** - 密码哈希

## 数据库配置

### 1. 安装MySQL

确保已安装MySQL 5.7+或MySQL 8.0+

### 2. 创建数据库连接

编辑 `.env` 文件，配置数据库连接信息：

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_database_password
DB_NAME=ai_chat_db

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-key-change-in-production-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 3. 初始化数据库

运行初始化脚本创建数据库表和默认用户：

```bash
cd ai-chat-backend
python init_db.py
```

初始化脚本会：
- 创建数据库 `ai_chat_db`
- 创建所有必要的表
- 创建默认管理员账户
- 创建测试用户账户

默认账户：
- **管理员**: admin / admin123456
- **测试用户**: testuser / test123456 (学号: 2024001)

## 安装依赖

```bash
cd ai-chat-backend
pip install -r requirements.txt
```

## API端点

### 认证相关

#### 1. 用户注册
```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "password123",
  "student_id": "2024002",
  "full_name": "新用户"
}
```

**响应**:
```json
{
  "success": true,
  "message": "注册成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "username": "newuser",
      "email": "newuser@example.com",
      "student_id": "2024002",
      "full_name": "新用户"
    }
  }
}
```

#### 2. 用户登录
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123456"
}
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### 3. 刷新Token
```http
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### 4. 获取当前用户信息
```http
GET /api/auth/me
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "student_id": null,
  "full_name": "系统管理员",
  "is_active": true,
  "is_admin": true,
  "created_at": "2024-01-01T00:00:00",
  "last_login": "2024-01-01T12:00:00"
}
```

#### 5. 更新用户资料
```http
PUT /api/auth/me
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "full_name": "更新后的姓名",
  "email": "newemail@example.com",
  "student_id": "2024003"
}
```

#### 6. 修改密码
```http
POST /api/auth/change-password
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "old_password": "oldpassword",
  "new_password": "newpassword123"
}
```

#### 7. 重置密码（通过邮箱）
```http
POST /api/auth/reset-password
Content-Type: application/json

{
  "email": "user@example.com"
}
```

#### 8. 用户登出
```http
POST /api/auth/logout
Authorization: Bearer <access_token>
```

#### 9. 获取用户列表（仅管理员）
```http
GET /api/auth/users?skip=0&limit=100
Authorization: Bearer <access_token>
```

#### 10. 删除用户（仅管理员）
```http
DELETE /api/auth/users/{user_id}
Authorization: Bearer <access_token>
```

## Token使用

### 访问受保护的端点

在请求头中添加Token：

```http
Authorization: Bearer <your_access_token>
```

### Token过期处理

1. **Access Token** 有效期：30分钟
2. **Refresh Token** 有效期：7天

当Access Token过期时，使用Refresh Token获取新的Access Token：

```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<your_refresh_token>"}'
```

## 数据库表结构

### users 表
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    student_id VARCHAR(20) UNIQUE,
    full_name VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login DATETIME
);
```

### sessions 表
```sql
CREATE TABLE sessions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    user_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);
```

### chat_history 表
```sql
CREATE TABLE chat_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id VARCHAR(100) NOT NULL,
    user_id INT,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    agent_type VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id)
);
```

## 启动服务

```bash
cd ai-chat-backend
python main.py
```

服务将在 `http://localhost:8000` 启动

## API文档

启动服务后，访问以下地址查看完整API文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 测试API

### 使用curl测试

1. 注册用户：
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser2",
    "email": "test2@example.com",
    "password": "test123456",
    "full_name": "测试用户2"
  }'
```

2. 登录：
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser2",
    "password": "test123456"
  }'
```

3. 获取用户信息：
```bash
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <your_access_token>"
```

### 使用Postman测试

1. 导入API端点
2. 设置环境变量（base_url, access_token等）
3. 使用Pre-request Script自动管理Token

## 安全建议

1. **生产环境必须修改**：
   - JWT_SECRET_KEY（至少32字符）
   - 默认管理员密码
   - 数据库密码

2. **密码策略**：
   - 最少6位
   - 建议使用复杂密码

3. **Token安全**：
   - Access Token有效期建议30分钟
   - Refresh Token有效期建议7天
   - 客户端应安全存储Token

4. **HTTPS**：
   - 生产环境必须使用HTTPS
   - 防止Token被窃取

## 常见问题

### 1. 数据库连接失败

检查：
- MySQL服务是否启动
- .env文件中的数据库配置是否正确
- 用户权限是否足够

### 2. Token无效

检查：
- Token是否过期
- JWT_SECRET_KEY是否一致
- Token格式是否正确

### 3. 密码错误

检查：
- 密码是否正确
- 用户名/邮箱是否正确
- 账户是否被禁用

## 扩展功能

### 添加邮箱验证

修改 `auth_routes.py` 中的 `register` 函数，添加邮箱验证逻辑。

### 添加第三方登录

集成OAuth2.0（微信、QQ、Google等）

### 添加双因素认证

使用TOTP或短信验证码

## 联系方式

如有问题，请提交Issue或联系开发团队。

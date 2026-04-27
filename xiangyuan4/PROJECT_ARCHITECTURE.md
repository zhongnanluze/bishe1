# 项目架构图

> 本项目是一个基于 **Vue 3 + FastAPI** 的 AI 智能问答系统，面向高校学生服务场景（沈阳工业大学）。

---

## 一、整体系统架构

```mermaid
graph TB
    subgraph Client["🖥️ 客户端层"]
        Browser["现代浏览器<br/>Chrome / Edge / Firefox"]
    end

    subgraph Frontend["🎨 前端层 (ai-chat-frontend)"]
        direction TB
        Vue3["Vue 3 + Vite"]
        Router["Vue Router 5<br/>HTML5 History 模式"]
        ECharts["ECharts 6 可视化"]
        WebGL["WebGL 特效<br/>Three.js / OGL / GLSL"]
        Services["Service 层<br/>apiService / authService"]
    end

    subgraph Backend["⚙️ 后端层 (ai-chat-backend)"]
        direction TB
        FastAPI["FastAPI + Uvicorn<br/>异步 ASGI"]
        AuthModule["🔐 认证模块<br/>JWT 双 Token + 密码哈希"]
        AgentSystem["🤖 多智能体系统<br/>5 类专业 Agent"]
        RAGModule["📚 RAG 检索增强<br/>Embedding + ChromaDB"]
        AdminModule["📊 管理员模块<br/>用量统计 + 趋势分析"]
        SessionMgr["💬 会话管理<br/>MySQL 持久化"]
    end

    subgraph DataLayer["🗄️ 数据持久化层"]
        direction TB
        MySQL[("MySQL<br/>ai_chat_db")]
        ChromaDB[("ChromaDB<br/>向量数据库")]
    end

    subgraph External["🌐 外部服务层"]
        direction TB
        DeepSeek["DeepSeek API<br/>大语言模型"]
        Aliyun["阿里云百炼<br/>Embedding API"]
        JWXT["沈阳工业大学<br/>正方教务系统<br/>(CDP 浏览器抓取)"]
    end

    Browser -->|"HTTP / SSE"| Vue3
    Vue3 --> Router
    Vue3 --> Services
    Services -->|"REST API + SSE 流式"| FastAPI
    Vue3 --> ECharts
    Vue3 --> WebGL

    FastAPI --> AuthModule
    FastAPI --> AgentSystem
    FastAPI --> RAGModule
    FastAPI --> AdminModule
    FastAPI --> SessionMgr

    AuthModule --> MySQL
    SessionMgr --> MySQL
    AdminModule --> MySQL
    RAGModule --> ChromaDB
    AgentSystem --> RAGModule

    AgentSystem -->|"LLM 调用"| DeepSeek
    RAGModule -->|"文本向量化"| Aliyun
    AgentSystem -->|"学业数据查询"| JWXT

    style Frontend fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style Backend fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    style DataLayer fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style External fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
```

---

## 二、前端详细架构

```mermaid
graph LR
    subgraph Entry["入口层"]
        index["index.html"]
        main["main.js<br/>创建 Vue 实例"]
        App["App.vue<br/><router-view>"]
    end

    subgraph RouterLayer["路由层 (src/router/)"]
        router["index.js"]
        guard["全局导航守卫<br/>权限校验 + Token 刷新"]
    end

    subgraph Views["页面视图层 (src/views/)"]
        Chat["Chat.vue<br/>核心聊天界面 ⭐"]
        KB["KnowledgeBase.vue<br/>知识库管理"]
        AdminV["Admin.vue + AdminDashboard.vue<br/>管理后台 + 数据可视化"]
        Login["Login.vue<br/>登录页"]
        Register["Register.vue<br/>注册页"]
        EasyLogin["EasyLogin.vue<br/>快捷登录(开发)"]
        Debug["Debug.vue<br/>调试工具"]
    end

    subgraph Components["公共组件 (src/component/)"]
        DarkVeil["DarkVeil.vue<br/>WebGL 暗色背景"]
    end

    subgraph VueBits["视觉特效库 (src/views/vueBits/)"]
        BorderGlow["BorderGlow.vue<br/>边框发光"]
        LineWaves["LineWaves.vue<br/>Canvas 波浪"]
        LiquidEther["LiquidEther.vue<br/>WebGL 液态效果"]
    end

    subgraph Services["服务层 (src/services/)"]
        apiService["apiService.js<br/>通用 HTTP + 自动 Token 刷新"]
        authService["authService.js<br/>认证 API 封装"]
    end

    index --> main --> App --> router
    router --> guard
    guard --> Chat
    guard --> KB
    guard --> AdminV
    guard --> Login
    guard --> Register
    guard --> EasyLogin
    guard --> Debug

    Chat --> apiService
    KB --> apiService
    AdminV --> apiService
    Login --> authService
    Register --> authService

    Login --> LineWaves
    Login --> BorderGlow
    Login --> DarkVeil

    style Chat fill:#ffebee,stroke:#b71c1c,stroke-width:2px
    style apiService fill:#e3f2fd,stroke:#0d47a1,stroke-width:2px
```

### 前端路由映射表

| 路由路径 | 对应组件 | 访问权限 |
|---------|---------|---------|
| `/` | → 重定向到 `/debug` | 公开 |
| `/debug` | Debug.vue | 公开 |
| `/login` | Login.vue | 未登录用户（`requiresGuest`） |
| `/register` | Register.vue | 未登录用户（`requiresGuest`） |
| `/easylogin` | EasyLogin.vue | 未登录用户（`requiresGuest`） |
| `/chat` | Chat.vue | 已登录用户（`requiresAuth`） |
| `/knowledge-base` | KnowledgeBase.vue | 已登录用户（`requiresAuth`） |
| `/admin` | Admin.vue + AdminDashboard.vue | 管理员（`requiresAuth + requiresAdmin`） |
| `/*` | → 重定向到 `/debug` | 公开 |

---

## 三、后端详细架构

```mermaid
graph TB
    subgraph MainApp["FastAPI 主应用 (main.py)"]
        direction TB
        app["FastAPI App"]
        cors["CORS 中间件"]
        lifespan["生命周期管理<br/>数据库初始化"]
    end

    subgraph Routes["API 路由层"]
        direction LR
        main_routes["main.py 路由<br/>对话 / 会话 / 智能体列表"]
        auth_routes["auth_routes.py<br/>注册 / 登录 / Token 刷新"]
        kb_routes["knowledge_base_routes.py<br/>知识库 CRUD / 搜索 / 上传"]
        admin_routes["admin_routes.py<br/>统计 / 趋势 / 概览"]
    end

    subgraph AgentSystem["🤖 智能体系统 (agents/)"]
        direction TB
        router["router.py<br/>LLM 意图分类 + 关键词降级"]
        base["base_agent.py<br/>抽象基类 AgentResponse"]

        chat["chat_agent.py<br/>日常聊天"]
        academic["academic_agent.py<br/>学业查询<br/>集成 jwxt_cli"]
        services["student_services_agent.py<br/>学生办事"]
        policy["policy_agent.py<br/>制度查询"]
        psych["psychology_agent.py<br/>心理咨询"]
    end

    subgraph AuthSystem["🔐 认证系统"]
        direction TB
        models["auth_models.py<br/>Pydantic 请求/响应模型"]
        utils["auth_utils.py<br/>SHA256 + JWT + 依赖注入"]
        routes["auth_routes.py<br/>10 个认证端点"]
    end

    subgraph ServicesB["服务层"]
        direction TB
        rag["rag_service.py<br/>Embedding + ChromaDB<br/>文本分段 + 语义搜索"]
        session["session_manager.py<br/>会话管理<br/>历史记录持久化"]
        db["database.py<br/>SQLAlchemy ORM + aiomysql"]
        env["env_utils.py<br/>环境变量读取"]
    end

    app --> cors --> lifespan
    app --> main_routes
    app --> auth_routes
    app --> kb_routes
    app --> admin_routes

    main_routes --> router
    router --> chat
    router --> academic
    router --> services
    router --> policy
    router --> psych

    chat --> rag
    academic --> rag
    services --> rag
    policy --> rag
    psych --> rag

    academic --> jwxt["jwxt_cli.py<br/>教务系统抓取"]

    main_routes --> session
    auth_routes --> AuthSystem
    kb_routes --> rag
    admin_routes --> db

    session --> db
    rag --> db

    style AgentSystem fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    style AuthSystem fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style ServicesB fill:#e1f5fe,stroke:#01579b,stroke-width:2px
```

### 后端 API 端点汇总

| 模块 | 路由前缀 | 核心端点 | 说明 |
|-----|---------|---------|-----|
| **核心对话** | `/api/` | `POST /chat` / `POST /stream` / `POST /direct` | 多轮对话 + SSE 流式 + 直连智能体 |
| **会话管理** | `/api/` | `GET/POST/DELETE /sessions/*` | 会话 CRUD + 历史记录 |
| **认证** | `/api/auth/` | `POST /register` / `POST /login` / `POST /refresh` 等 | JWT 双 Token 认证体系 |
| **知识库** | `/api/knowledge-base/` | `GET/POST/PUT/DELETE /entries` / `POST /search` / `POST /upload` | 知识库管理 + 语义搜索 + 文件上传 |
| **管理后台** | `/api/admin/` | `GET /overview` / `GET /stats/users` / `GET /stats/agents` / `GET /trends` | 用量统计与趋势分析 |

---

## 四、数据库 E-R 架构

```mermaid
erDiagram
    users ||--o{ sessions : "拥有"
    users ||--o{ usage_logs : "产生"
    sessions ||--o{ chat_history : "包含"

    users {
        int id PK
        string username UK
        string email UK
        string password_hash
        string student_id
        boolean is_admin
        datetime created_at
    }

    sessions {
        string session_id PK
        int user_id FK
        string topic
        datetime expires_at
        boolean is_active
    }

    chat_history {
        int id PK
        string session_id FK
        string role "user/assistant"
        text content
        string agent_type
        datetime created_at
    }

    knowledge_base {
        int id PK
        string title
        text content
        string category
        string agent_type
        datetime created_at
    }

    usage_logs {
        int id PK
        int user_id FK
        string agent_type
        int prompt_tokens
        int completion_tokens
        int total_tokens
        datetime created_at
    }
```

---

## 五、智能体路由与工具链

```mermaid
graph LR
    User["用户输入"]
    Router["AgentRouter<br/>意图分类"]

    subgraph Agents["5 类专业智能体"]
        Chat["💬 ChatAgent<br/>日常闲聊<br/>工具: 无"]
        Academic["🎓 AcademicAgent<br/>学业查询<br/>工具: 课表/成绩/选课/GPA/日历"]
        Services["📋 StudentServicesAgent<br/>学生办事<br/>工具: 证件/缴费/饭卡/流程"]
        Policy["📖 PolicyAgent<br/>制度查询<br/>工具: 制度检索/部门联系"]
        Psych["🧠 PsychologyAgent<br/>心理咨询<br/>工具: 咨询信息/自评/预约/求助"]
    end

    RAG["RAGService<br/>知识库检索"]
    LLM["DeepSeek API<br/>大语言模型"]

    User --> Router
    Router -->|分类结果| Chat
    Router -->|分类结果| Academic
    Router -->|分类结果| Services
    Router -->|分类结果| Policy
    Router -->|分类结果| Psych

    Chat --> RAG
    Academic --> RAG
    Services --> RAG
    Policy --> RAG
    Psych --> RAG

    Chat --> LLM
    Academic --> LLM
    Services --> LLM
    Policy --> LLM
    Psych --> LLM

    style Router fill:#ffebee,stroke:#b71c1c,stroke-width:2px
    style RAG fill:#fff3e0,stroke:#e65100,stroke-width:2px
```

---

## 六、数据流向图（一次完整对话）

```mermaid
sequenceDiagram
    actor U as 用户
    participant F as 前端 Vue3
    participant API as FastAPI
    participant Router as AgentRouter
    participant RAG as RAGService
    participant Chroma as ChromaDB
    participant Agent as 专业Agent
    participant LLM as DeepSeek API
    participant DB as MySQL

    U->>F: 输入问题
    F->>API: POST /api/stream<br/>+ session_id + message
    API->>DB: 查询会话历史
    DB-->>API: 返回历史记录
    API->>Router: route_query(message)
    Router->>LLM: 意图分类请求
    LLM-->>Router: 返回 AgentType
    Router-->>API: 路由到对应 Agent

    API->>RAG: semantic_search(query)
    RAG->>Chroma: 向量相似度检索
    Chroma-->>RAG: 返回 Top-K 文档
    RAG-->>API: 返回检索上下文

    API->>Agent: stream_process(query, context, history)
    Agent->>LLM: 构造 Prompt + 流式请求
    LLM-->>Agent: SSE 逐字返回
    Agent-->>API: yield 流式响应
    API-->>F: SSE 转发给用户
    F-->>U: 逐字显示回复

    API->>DB: 保存聊天记录
    API->>DB: 记录 Token 用量
```

---

## 七、技术栈总览

### 前端
| 类别 | 技术 |
|-----|------|
| 框架 | Vue 3.5 + Vite 7 |
| 路由 | Vue Router 5 (HTML5 History) |
| 状态管理 | 无集中式 (localStorage + 组件内部状态) |
| HTTP 请求 | 原生 fetch + 自定义封装 |
| 图表可视化 | ECharts 6 + vue-echarts |
| Markdown 渲染 | marked 18 |
| 3D/特效 | Three.js + OGL + 自定义 GLSL Shader |

### 后端
| 类别 | 技术 |
|-----|------|
| Web 框架 | FastAPI + Uvicorn (ASGI) |
| ORM | SQLAlchemy 2.0 + aiomysql (异步) |
| LLM 框架 | LangChain + langchain-deepseek |
| 向量数据库 | ChromaDB 0.5+ |
| Embedding | 阿里云百炼 API / Sentence-Transformer 本地回退 |
| 认证 | python-jose (JWT) + passlib (bcrypt) |
| Token 计数 | tiktoken |
| 文件解析 | PyPDF2 + python-docx |

### 基础设施
| 类别 | 技术 |
|-----|------|
| 数据库 | MySQL (ai_chat_db) |
| 向量库 | ChromaDB (本地持久化) |
| LLM 服务 | DeepSeek API |
| 外部数据 | 正方教务系统 (CDP 浏览器协议) |

---

## 八、项目目录总览

```
xiangyuan4/                              # 项目根目录
├── ai-chat-frontend/                    # 🎨 前端项目
│   ├── src/
│   │   ├── main.js                      # 应用入口
│   │   ├── App.vue                      # 根组件
│   │   ├── router/index.js              # 路由配置 + 导航守卫
│   │   ├── services/
│   │   │   ├── apiService.js            # HTTP 请求封装
│   │   │   └── authService.js           # 认证 API
│   │   ├── views/
│   │   │   ├── Chat.vue                 # ⭐ 核心聊天界面
│   │   │   ├── KnowledgeBase.vue        # 知识库管理
│   │   │   ├── Admin.vue                # 管理后台布局
│   │   │   ├── AdminDashboard.vue       # 数据可视化仪表盘
│   │   │   ├── Login.vue                # 登录页
│   │   │   ├── Register.vue             # 注册页
│   │   │   ├── EasyLogin.vue            # 快捷登录
│   │   │   ├── Debug.vue                # 调试页
│   │   │   └── vueBits/                 # 视觉特效组件
│   │   │       ├── BorderGlow.vue
│   │   │       ├── LineWaves.vue
│   │   │       └── LiquidEther.vue
│   │   └── component/DarkVeil/          # 公共 WebGL 背景
│   ├── package.json
│   └── vite.config.js
│
└── ai-chat-backend/                     # ⚙️ 后端项目
    ├── main.py                          # FastAPI 主入口
    ├── database.py                      # SQLAlchemy ORM + 5 张表
    ├── rag_service.py                   # RAG 核心服务
    ├── session_manager.py               # 会话管理
    ├── auth_routes.py                   # 认证路由 (10 端点)
    ├── auth_models.py                   # Pydantic 认证模型
    ├── auth_utils.py                    # JWT + 密码哈希工具
    ├── knowledge_base_routes.py         # 知识库路由 (8 端点)
    ├── admin_routes.py                  # 管理后台路由 (5 端点)
    ├── env_utils.py                     # 环境变量读取
    ├── jwxt_cli.py                      # 教务系统 CLI 工具
    ├── init_db.py                       # 数据库初始化
    ├── fix_db.py                        # 数据库修复脚本
    ├── .env                             # 环境变量配置
    ├── requirements.txt
    └── agents/                          # 🤖 智能体模块
        ├── __init__.py
        ├── base_agent.py                # 抽象基类
        ├── router.py                    # 智能体路由
        ├── chat_agent.py                # 日常聊天
        ├── academic_agent.py            # 学业查询
        ├── student_services_agent.py    # 学生办事
        ├── policy_agent.py              # 制度查询
        └── psychology_agent.py          # 心理咨询
```

---

*架构文档生成时间: 2026-04-25*

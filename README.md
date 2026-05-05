# wecom-ai-agent

一个部署在企业微信的智能客服系统，基于 RAG（Retrieval-Augmented Generation）架构实现。

## 功能特性

### 🎯 核心功能
- **FAQ智能检索**: 基于混合检索（BM25 + 向量检索）的知识库问答
- **对话状态管理**: 有限状态机（FSM）控制对话流程
- **预约服务**: 支持种植牙、正畸、洗牙等服务的预约
- **风险拦截**: 敏感词检测和人工转接机制
- **数据库存储**: SQLite + SQLAlchemy 持久化预约数据

### ✨ 增强版RAG功能（V2.0）
1. **Query Rewrite**: LLM参与理解用户问题，生成多版本改写查询
2. **Hybrid Retrieval**: BM25关键词检索 + 向量语义检索 + RRF融合
3. **Rerank模块**: LLM对候选文档进行精排，提升相关性
4. **Prompt约束**: 严格的输出约束，减少幻觉
5. **LLM-as-a-Judge**: 基于LLM的回答质量评估体系

## 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     企业微信入口                                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI 服务                                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Agent Core (优先级处理)                      │
│  1. 风险拦截 → 2. 人工转接 → 3. 退出意图 → 4. 预约流程          │
│  5. RAG检索 → 6. LLM兜底                                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  状态机     │    │   RAG模块   │    │   工具调用   │
│ (FSM)       │    │ (增强版)    │    │ (ToolRegistry)│
└─────────────┘    └─────────────┘    └─────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│Session管理  │    │FAQ知识库    │    │  预约服务    │
│             │    │BM25+向量    │    │  时间查询    │
└─────────────┘    └─────────────┘    └─────────────┘
                            │
                            ▼
                   ┌─────────────┐
                   │  SQLite DB  │
                   └─────────────┘
```

## 项目结构

```
app/
├── agent/                    # 核心Agent模块
│   ├── core.py              # 主入口，优先级处理逻辑
│   ├── rag_enhanced.py      # 增强版RAG模块（Query Rewrite + Hybrid + Rerank）
│   ├── faq.py               # 基础FAQ检索（兼容旧版）
│   ├── session.py           # 状态机管理
│   ├── tools.py             # 工具注册与调用
│   ├── risk_guard.py        # 风险拦截
│   └── prompts.py           # 提示词模板
├── services/                # 业务服务
│   ├── appointment.py       # 预约服务
│   └── database.py          # 数据库模型
├── wecom/                   # 企业微信集成
│   ├── handler.py           # 消息处理器
│   └── crypto.py            # 加解密
├── config/                  # 配置
│   └── settings.py          # 环境变量配置
└── main.py                  # FastAPI入口
```

## 本地启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
pip install faiss-cpu numpy
```

### 2. 配置环境变量

```bash
export WECOM_TOKEN=your_token
export WECOM_AES_KEY=your_aes_key
export WECOM_CORP_ID=your_corp_id
export QWEN_API_KEY=your_qwen_api_key  # 可选，用于增强RAG功能
```

### 3. 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. 开发调试

服务启动后可通过调试接口测试：

```bash
# 健康检查
curl http://localhost:8000/

# 对话测试
curl "http://localhost:8000/dev/chat?msg=种植牙多少钱"
```

## 核心组件说明

### RAG增强模块 (`app/agent/rag_enhanced.py`)

| 组件 | 说明 |
|------|------|
| **QueryRewriter** | LLM驱动的查询重写，生成多版本查询 |
| **BM25Retriever** | 基于字符级分词的关键词检索 |
| **VectorRetriever** | Faiss向量索引的语义检索 |
| **HybridRetriever** | BM25 + 向量 + RRF融合 |
| **Reranker** | LLM精排，提升排序质量 |
| **RAGGenerator** | 基于上下文的回答生成 |
| **LLMEvaluator** | LLM-as-a-Judge评估体系 |

### 状态机 (`app/agent/session.py`)

| 状态 | 说明 | 可转换 |
|------|------|--------|
| `consulting` | 咨询中 | → appointment_collecting, handoff_pending |
| `appointment_collecting` | 预约信息收集 | → appointment_completed, consulting |
| `handoff_pending` | 等待人工转接 | 不可转换 |
| `appointment_completed` | 预约完成 | → consulting |

## 云服务器部署（Ubuntu + systemd + Nginx）

### 1. 安装依赖

```bash
git clone <repo_url>
cd wecom-ai-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install fastapi uvicorn requests wechatpy pycryptodome python-dotenv faiss-cpu numpy
```

### 2. systemd 配置

```ini
# /etc/systemd/system/wecom-ai-agent.service
[Unit]
Description=wecom ai agent
After=network.target

[Service]
User=root
WorkingDirectory=/root/project/wecom-ai-agent

# ❗关键：环境变量不要加引号
Environment=WECOM_TOKEN=svvikhfo7KonGCV
Environment=WECOM_AES_KEY=OUYuidmBQa5XWr3ngBi7lXFj6PPM6cVIwFMk9vKJUfG
Environment=WECOM_CORP_ID=ww2889b92a919d6de7
Environment=QWEN_API_KEY=sk-a74ccef85bab443db01407504119889a

# ❗关键：监听0.0.0.0 + access log
ExecStart=/root/project/wecom-ai-agent/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --access-log --log-level info

Restart=always
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable wecom-ai-agent
sudo systemctl start wecom-ai-agent
```

### 3. Nginx 反向代理

```nginx
# /etc/nginx/conf.d/wecom-ai-agent.conf
server {
    listen 443 ssl http2 default_server;
    listen [::]:443 ssl http2 default_server;

    server_name leqi-ai.online;

    ssl_certificate     /etc/letsencrypt/live/leqi-ai.online/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/leqi-ai.online/privkey.pem;

    client_max_body_size 10m;

    location /wecom/callback {
        proxy_pass http://127.0.0.1:8000;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

## 企业微信回调配置

在企业微信应用配置中填写：

- **URL**: `https://your-domain.com/wecom/callback`
- **Token**: 与 `WECOM_TOKEN` 一致
- **EncodingAESKey**: 与 `WECOM_AES_KEY` 一致

## 配置说明

| 环境变量 | 说明 | 必填 |
|----------|------|------|
| `WECOM_TOKEN` | 企业微信Token | 是 |
| `WECOM_AES_KEY` | 企业微信AES密钥 | 是 |
| `WECOM_CORP_ID` | 企业微信CorpID | 是 |
| `QWEN_API_KEY` | 阿里云Qwen API密钥 | 否（增强功能需要）|

## 设计原则

1. **最小权限原则**: LLM仅用于自然语言生成，禁止执行关键操作
2. **职责分离**: 状态机管流程，LLM管语言，工具管操作
3. **FSM优先**: 先检查状态规则，再调用LLM
4. **防幻觉**: 严格的输出验证和prompt约束

## 许可证

MIT License
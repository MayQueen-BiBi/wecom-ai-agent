# wecom-ai-agent

一个部署在企业微信的智能客服系统，基于 RAG（Retrieval-Augmented Generation）架构实现，支持多用户会话管理和意图驱动的对话流程。

## 功能特性

### 🎯 核心功能
- **FAQ智能检索**: 基于混合检索（BM25 + 向量检索）的知识库问答
- **对话状态管理**: 有限状态机（FSM）控制对话流程，支持栈式状态管理
- **预约服务**: 支持种植牙、正畸、洗牙等服务的预约
- **风险拦截**: 敏感词检测和人工转接机制
- **数据库存储**: SQLite + SQLAlchemy 持久化预约、医生、排班数据
- **员工/外部用户区分**: 支持企业微信内部员工和外部用户的权限区分

### ✨ 增强版RAG功能（V2.0）
1. **Query Rewrite**: LLM参与理解用户问题，生成多版本改写查询
2. **Hybrid Retrieval**: BM25关键词检索 + 向量语义检索 + RRF融合
3. **Rerank模块**: LLM对候选文档进行精排，提升相关性
4. **Prompt约束**: 严格的输出约束，减少幻觉
5. **LLM-as-a-Judge**: 基于LLM的回答质量评估体系

### 🧠 意图驱动架构（V3.0）
- **4层架构设计**: MEDICAL_KNOWLEDGE → USER_DECISION → OBJECTION_HANDLING → BUSINESS_CONVERSION
- **12个核心意图**:
  - **Symptom_Check**: 症状咨询
  - **Procedure_Explain**: 治疗流程解释
  - **Process_Flow**: 就诊流程指引
  - **Price_Inquiry**: 价格咨询
  - **Comparative_Analysis**: 方案对比
  - **Risk_Assessment**: 风险评估
  - **Fear_Relief**: 恐惧缓解
  - **Price_Objection**: 价格异议处理
  - **Trust_Verification**: 信任验证
  - **Lead_Generation**: 预约转化
  - **Logistics_Support**: 后勤支持
  - **Out_of_Scope**: 超出范围

### 💾 语义缓存
- 基于向量相似度的高频问题缓存
- 支持缓存命中时直接返回，降低推理成本
- 可配置缓存有效期和相似度阈值

### 👨‍⚕️ 医生管理系统
- 医生信息管理（姓名、职称、擅长领域）
- 排班管理（可预约时间、已预约状态）
- 智能医生推荐（基于症状和排班匹配）

## 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     企业微信入口                                  │
│              (区分内部员工/外部用户)                              │
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
        ┌───────────────────┼───────────────────┬───────────────┐
        ▼                   ▼                   ▼               ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐   ┌─────────────┐
│  状态机     │    │   RAG模块   │    │ 意图分类器  │   │  语义缓存   │
│ (FSM)       │    │ (增强版)    │    │(12意图)    │   │ (Semantic) │
└─────────────┘    └─────────────┘    └─────────────┘   └─────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│Session管理  │    │FAQ知识库    │    │  工具调用    │
│ (多用户)    │    │BM25+向量    │    │ (ToolRegistry)│
└─────────────┘    └─────────────┘    └─────────────┘
                            │                   │
                            ▼                   ▼
                   ┌─────────────────────────────────┐
                   │          SQLite DB              │
                   │  Doctor | Schedule | Appointment│
                   └─────────────────────────────────┘
```

## 项目结构

```
app/
├── agent/                    # 核心Agent模块
│   ├── core.py              # 主入口，优先级处理逻辑
│   ├── rag_enhanced.py      # 增强版RAG模块（Query Rewrite + Hybrid + Rerank）
│   ├── faq.py               # 基础FAQ检索（兼容旧版）
│   ├── state_machine.py     # 状态机管理（栈式状态管理）
│   ├── intent_classifier.py # 意图分类器（12核心意图）
│   ├── tools.py             # 工具注册与调用
│   ├── risk_guard.py        # 风险拦截
│   ├── prompts.py           # 提示词模板
│   └── semantic_cache.py    # 语义缓存
├── services/                # 业务服务
│   ├── appointment.py       # 预约服务
│   ├── doctor_service.py    # 医生服务
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

### 状态机 (`app/agent/state_machine.py`)

| 状态 | 说明 | 可转换 |
|------|------|--------|
| `consulting` | 咨询中 | → appointment_collecting, handoff_pending |
| `appointment_collecting` | 预约信息收集 | → appointment_completed, consulting |
| `handoff_pending` | 等待人工转接 | 不可转换 |
| `appointment_completed` | 预约完成 | → consulting |

**状态管理特性**:
- 栈式状态管理，支持状态挂起和恢复
- 增量槽位更新，不覆盖已有值
- 多用户会话隔离

### 意图分类器 (`app/agent/intent_classifier.py`)

| 意图 | 关键词示例 | 对应层级 |
|------|-----------|----------|
| Symptom_Check | 牙齿松动、牙龈出血、牙疼 | MEDICAL_KNOWLEDGE |
| Procedure_Explain | 根管治疗、种牙过程 | MEDICAL_KNOWLEDGE |
| Process_Flow | 怎么挂号、就诊流程 | MEDICAL_KNOWLEDGE |
| Price_Inquiry | 多少钱、价格、费用 | USER_DECISION |
| Comparative_Analysis | 哪种好、对比、区别 | USER_DECISION |
| Risk_Assessment | 风险、后遗症、成功率 | OBJECTION_HANDLING |
| Fear_Relief | 疼不疼、害怕、紧张 | OBJECTION_HANDLING |
| Price_Objection | 太贵、便宜点、优惠 | OBJECTION_HANDLING |
| Trust_Verification | 医生资质、案例、职称 | OBJECTION_HANDLING |
| Lead_Generation | 预约、挂号、安排时间 | BUSINESS_CONVERSION |
| Logistics_Support | 地址、营业时间、停车 | BUSINESS_CONVERSION |
| Out_of_Scope | 无关问题 | - |

### 数据库模型 (`app/services/database.py`)

| 表名 | 字段 | 说明 |
|------|------|------|
| **Doctor** | id, name, title, specialty, description | 医生信息 |
| **Schedule** | id, doctor_id, date, time_slot, is_available | 排班信息 |
| **Appointment** | id, user_id, doctor_id, date, time_slot, status, visit_notes | 预约信息 |

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
Environment=WECOM_TOKEN=your_token
Environment=WECOM_AES_KEY=your_aes_key
Environment=WECOM_CORP_ID=your_corp_id
Environment=QWEN_API_KEY=your_qwen_api_key  # 可选，用于增强RAG功能

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
5. **可观测性**: 完整的日志记录和监控指标

## 许可证

MIT License
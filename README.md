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

## 技术架构（当前生产链路）

```
企业微信 / 浏览器 HTTP
        │
        ▼
┌───────────────────┐     AgentRequest / AgentResponse（契约见 app/api/protocol.py）
│  FastAPI (main)   │ ──► /wecom/callback、/dev/chat 等
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐     超时、并发信号量、final_hook 日志
│  app/api/entry    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐     Graph Runtime（run_graph + DENTAL_GRAPH）
│ app/workflows/    │ ──► nodes：intercept → understanding → … → execution
└─────────┬─────────┘
          │
    ┌─────┴─────┬─────────────┐
    ▼           ▼             ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│routing/  │ │execution│ │understanding
│YAML策略 │ │core_exec│ │统一理解  │
└─────────┘ └────┬────┘ └─────────┘
                 │
                 ▼
          ┌─────────────┐
          │ app/core/   │  LLM、工具、缓存、状态机、守卫、FAQ 数据
          └──────┬──────┘
                 │
                 ▼
          ┌─────────────┐
          │ app/state/  │  AgentRunState + reducers + session_store
          └─────────────┘
                 │
                 ▼
          ┌─────────────┐
          │ services/   │  SQLite：医生、排班、预约
          └─────────────┘
```

说明：**已不再使用 `app/agent`**；依赖防火墙见 `app/guards/dependency_guard.py` 与 `app/DEPENDENCY_RULES_FINAL.md`。

## 项目结构

```
app/
├── api/                     # HTTP/集成统一入口（handle_request → workflow）
│   └── entry.py
├── workflows/               # Graph 编排（dental 等）
├── execution/               # 纯执行（core_executor、RAG、牙科执行层）
├── core/                    # LLM、工具、缓存、状态机、守卫、FAQ 数据
├── routing/                 # 策略路由（YAML policy engine）
├── state/                   # AgentRunState、reducers、session_store
├── understanding/           # 意图与统一理解
├── observability/           # trace、metrics、FlowTracker
├── guards/                  # dependency_guard 等
├── services/                # 业务服务
│   ├── appointment.py       # 预约服务
│   ├── doctor_service.py    # 医生服务
│   └── database.py          # 数据库模型
├── wecom/                   # 企业微信集成
│   ├── entry.py             # Webhook 解密 + 异常保护（主路径）
│   ├── handler.py           # 对 entry 的 re-export（兼容旧 import）
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

### RAG增强模块 (`app/execution/rag_enhanced.py`)

| 组件 | 说明 |
|------|------|
| **QueryRewriter** | LLM驱动的查询重写，生成多版本查询 |
| **BM25Retriever** | 基于字符级分词的关键词检索 |
| **VectorRetriever** | Faiss向量索引的语义检索 |
| **HybridRetriever** | BM25 + 向量 + RRF融合 |
| **Reranker** | LLM精排，提升排序质量 |
| **RAGGenerator** | 基于上下文的回答生成 |
| **LLMEvaluator** | LLM-as-a-Judge评估体系 |

### 状态机 (`app/core/runtime/state_machine.py`)

业务层使用 **栈式 `AgentState` 枚举**（如 `MEDICAL_KNOWLEDGE`、`USER_DECISION`、`BUSINESS_CONVERSION` 等），与意图矩阵联动；**不是**旧的 `consulting/appointment_collecting` 命名。详见源码中 `CORE_TRANSITIONS` 与 `ConversationContext`。

### 意图分类器 (`app/understanding/intent_classifier.py`)

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

1. **统一入口**: 业务只经 `app/api/entry.handle_request(AgentRequest)`（契约版本 `CONTRACT_VERSION`）
2. **编排与执行分离**: `workflows` 管图与节点；`execution` 管 state+action→结果；`routing` 仅 YAML 策略
3. **状态可约简**: `AgentRunState` + reducer 写回；会话副作用由 workflow 收口
4. **防幻觉与降级**: 检索守卫、critic、入口超时、`core/runtime/fallback` 高风险话术
5. **可观测与验收**: `RequestTrace` / `final_hook`；分层测试见 `tests/smoke/`、`tests/acceptance/`
6. **依赖防火墙**: `scripts/check_dependency.py`、`scripts/check_entry_contract.py`（CI 已挂）

## 许可证

MIT License
# wecom-ai-agent
一个部署在企业微信智能客服的demo

## 本地启动

1. 复制环境变量模板并填值

```bash
cp .env.example .env
```

2. 导出环境变量（或使用你自己的方式注入）

```bash
export WECOM_TOKEN=xxx
export WECOM_AES_KEY=xxx
export WECOM_CORP_ID=xxx
export QWEN_API_KEY=xxx
```

3. 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 云服务器部署（Ubuntu + systemd + Nginx）

1. 准备服务器（放行 80/443）
2. 安装 Python 3.11+、Nginx、git
3. 拉取项目并创建虚拟环境

```bash
git clone <your_repo_url>
cd wecom-ai-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install fastapi uvicorn requests wechatpy
```

4. 配置环境变量（建议写到 systemd service 中）
5. 使用 systemd 启动

```ini
# /etc/systemd/system/wecom-ai-agent.service
[Unit]
Description=wecom ai agent
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/wecom-ai-agent
Environment=WECOM_TOKEN=xxx
Environment=WECOM_AES_KEY=xxx
Environment=WECOM_CORP_ID=xxx
Environment=QWEN_API_KEY=xxx
ExecStart=/home/ubuntu/wecom-ai-agent/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable wecom-ai-agent
sudo systemctl start wecom-ai-agent
sudo systemctl status wecom-ai-agent
```

6. Nginx 反向代理 + HTTPS（用 certbot 申请证书）

```nginx
server {
    listen 80;
    server_name your.domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 企业微信回调配置

在企业微信应用配置中填写：

- URL: `https://your.domain.com/wecom/callback`
- Token: 与 `WECOM_TOKEN` 一致
- EncodingAESKey: 与 `WECOM_AES_KEY` 一致
- CorpID: 与 `WECOM_CORP_ID` 一致

保存后平台会先发起 GET 校验，再推送 POST 消息。

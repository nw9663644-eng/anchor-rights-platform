# 网络主播与 MCN 机构用工关系评估及权益保障平台

面向网络主播、MCN 机构、研究人员与平台管理员的法律科技平台。系统以网络主播用工关系识别为核心，将结构化评估、权益风险筛查、证据归集、案例法规检索、AI 问答和人工复核连接为可持续处理流程。

> 平台输出仅用于学习、研究和辅助分析，不构成正式法律意见。具体争议处理、劳动仲裁、诉讼或合同审查应咨询具有执业资格的专业人员。

## 核心能力

- 普通用户与管理员双角色登录，服务端校验权限并隔离数据
- 36 项事实核查：10 项人身、9 项经济、7 项组织从属性计分，以及 10 项不计分权益筛查
- 按 80/50/30 分界输出四类关系判断，并解释维度得分、触发事实和风险标签
- 问卷草稿、历史报告恢复，以及从报告一键建立权益事项
- 证据文件上传、访问控制、加密存档、下载与删除，单文件上限 15 MB
- 案例、法规和知识库检索；管理员可新增、批量导入和删除内容
- AI 问答由后端统一转发，API 密钥不进入前端；支持人工复核工作流
- 登录失败锁定、安全响应头、操作审计、数据库备份与服务健康守护
- SQLite 开箱即用，并预留 `DATABASE_URL` 切换 PostgreSQL

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | React、TypeScript、Vite、Recharts、Lucide React |
| 后端 | Python、FastAPI、Uvicorn |
| 数据 | SQLite，预留 PostgreSQL |
| 部署 | Windows Server 或 Ubuntu、Nginx、PowerShell、HTTPS |

## 项目结构

```text
anchor-rights-platform/
├── backend/
│   ├── app/                 # API、鉴权、评估、存储、AI 与安全逻辑
│   ├── tests/               # 后端自动化测试
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/                 # React 页面与样式
│   ├── package.json
│   └── vite.config.ts
├── deploy/
│   ├── windows-deploy.ps1   # Windows 安装、启动、守护与备份
│   ├── windows-https.ps1    # 公网 IP HTTPS 与证书自动更新
│   ├── harden-ubuntu.sh
│   └── nginx-security.conf
├── SECURITY.md
├── serve-public-demo.mjs
└── start-public-demo.ps1
```

## 本地开发

后端：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

前端：

```powershell
cd frontend
npm ci
npm run dev
```

生产构建：

```powershell
cd frontend
npm ci
npm run build
```

临时公网演示可运行 `start-public-demo.ps1`。临时链接依赖本机和网络持续在线，不等于正式部署。

## Windows 云服务器部署

先完成前端生产构建，再以管理员身份运行：

```powershell
.\deploy\windows-deploy.ps1
```

该脚本会注册平台开机启动、两分钟健康检查守护和每日数据库备份。

若要通过公网 IP 启用可信 HTTPS，请先将 `lego.exe` 放到服务器的 `C:\anchor-rights-platform\https-tools`，并在云平台和 Windows 防火墙放通 TCP 443，然后运行：

```powershell
.\deploy\windows-https.ps1 -PublicIp "服务器公网IP"
```

HTTPS 脚本会申请短期 IP 证书、注册 443 服务并每两天自动更新证书。

## 环境配置

复制 `backend/.env.example` 为 `backend/.env`，按实际环境填写管理员账号、AI 接口和数据库配置。首次启动会读取 `ADMIN_EMAIL` 和 `ADMIN_PASSWORD`；公开使用前必须更换初始化密码。

禁止提交以下运行数据：

```text
backend/.env
backend/.data_key
backend/platform.db
backend/uploads/
backend/.venv/
frontend/node_modules/
frontend/dist/
logs/
lego-data/
*.key
```

## 案例批量导入

后台接受 JSON 文件，例如：

```json
{
  "cases": [
    {
      "title": "案例标题",
      "relation": "标准劳动关系",
      "year": 2026,
      "focus": ["排班", "工资"],
      "summary": "裁判要点或案例摘要",
      "similarity": 60
    }
  ]
}
```

## 验证

```powershell
cd backend
python -m pytest -q

cd ..\frontend
npm run build
npm audit --omit=dev
```

当前版本验证结果：后端 8 项测试通过，前端生产构建通过，生产依赖审计无已知漏洞。

## 正式运营建议

- 使用 PostgreSQL、对象存储和已备案域名
- 定期执行异地备份并演练恢复
- 完善隐私政策、用户协议、数据导出与删除流程
- 持续维护法规版本、AI 权威引用和人工复核记录
- 扩充端到端测试、监控告警和安全审计

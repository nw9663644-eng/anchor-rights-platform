# 网络主播与 MCN 用工关系评估及权益保障平台

面向网络主播、MCN 机构、研究人员和管理员的法律科技工作台。平台以 2026.07 版 36 题规则模型为核心，将关系评估、权益缺口、证据归集、案例法规与 AI 问答连接为持续处理流程。

## 已实现

- 账号注册、登录、7 天会话与管理员权限
- 用户级评估、事项和证据数据隔离
- 10 项人身、9 项经济、7 项组织从属性计分，以及 10 项不计分权益筛查
- 80/50/30 分四档关系判断和可解释维度结果
- 问卷草稿、报告恢复和报告一键建立权益事项
- 真实证据文件上传、权限校验、下载与删除，单文件上限 15MB
- 案例、法规、知识库检索；管理员新增、批量导入和删除案例
- AI 问答由后端转发，API 密钥不进入前端
- SQLite 本地运行，并预留 `DATABASE_URL` 切换 PostgreSQL

## 本地启动

后端：

```powershell
cd D:\legal\anchor-rights-platform\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

生产前端与 API 代理：

```powershell
cd D:\legal\anchor-rights-platform\frontend
npm run build
cd ..
node serve-public-demo.mjs
```

访问 `http://127.0.0.1:8088`。

临时公网演示可运行 `D:\legal\anchor-rights-platform\start-public-demo.ps1`。该链接依赖本机和网络持续在线，不等于正式部署。

## 管理员

首次启动会读取 `backend/.env` 中的 `ADMIN_EMAIL` 和 `ADMIN_PASSWORD`。未配置时仅用于本地初始化的默认账号为 `admin@anchor-rights.local`，默认密码必须在公开使用前更换。

参照 `backend/.env.example` 管理配置。不要提交真实 `.env`、数据库或证据文件。

## 案例批量导入

后台接受 JSON 文件，格式如下：

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
cd D:\legal\anchor-rights-platform\backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

cd D:\legal\anchor-rights-platform\frontend
npm run build
```

## 上线前仍需完成

- 更换管理员密码和已使用的 AI 密钥
- 使用 PostgreSQL、对象存储、HTTPS 正式域名和定时备份
- 补充隐私政策、用户协议、数据删除与 AI 敏感信息提示
- 增加法规内容版本管理、AI 权威引用和更完整的端到端测试

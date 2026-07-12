# 网络主播与 MCN 机构用工关系评估及权益保障平台

一个面向网络主播、MCN 机构、研究人员与平台管理员的法律科技 SaaS 原型系统。平台围绕网络主播与 MCN 机构之间的用工关系识别、权益风险筛查、证据归集、案例检索、法规学习和 AI 问答构建，帮助用户以结构化方式完成关系评估和权益保障分析。

## 项目定位

本平台聚焦新业态劳动关系中的网络主播场景，试图解决传统法律判断标准与平台化用工模式之间的错配问题。系统以“人格从属性、经济从属性、组织从属性”为核心评估框架，并结合社保缺口、报酬结算、账号控制、排班考勤、违约金、封号处罚、内容管理等常见风险点，形成可解释的评估报告。

平台不是简单的展示页，而是一个前后端一体的可运行系统，包含用户登录、智能问卷、评估报告、案例库、法规汇总、知识库、证据清单、AI 问答和后台管理等模块。

## 核心功能

- 智能评估问卷：围绕三从属性和权益风险设置结构化问题，支持用户完成用工关系评估。
- 关系类型判断：按照总分区间输出四类关系判断结果，包括标准劳动关系、新业态模糊混合用工关系、劳务依附型合作关系、纯平等民事商务合作关系。
- 结果报告生成：展示综合结论、维度得分、风险标签、证据建议、案例匹配和法规依据。
- 案例库检索：支持案例关键词检索、分类筛选、单条录入、批量导入和删除管理。
- 法规汇总：整理与劳动关系、民事合同、社会保险、平台治理、争议处理相关的法律法规和官方链接。
- 知识库管理：支持知识条目检索，并可通过后台持续补充法律观点、规则说明和研究资料。
- 证据清单：支持围绕合同、聊天记录、工资流水、排班考勤、账号管理等证据进行归集和管理。
- AI 问答：通过后端统一转发大模型接口，避免前端暴露 API 密钥，并结合平台知识内容回答用户问题。
- 后台管理：管理员可维护案例、知识库、法规依据、问卷配置、权重模型和系统设置。

## 技术栈

前端：

- React
- TypeScript
- Vite
- Recharts
- Lucide React

后端：

- Python
- FastAPI
- Uvicorn
- SQLite
- PostgreSQL 预留支持

部署：

- Ubuntu Server
- Nginx
- Node.js
- Python venv

## 项目结构

```text
anchor-rights-platform/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── auth.py
│   │   ├── evaluator.py
│   │   ├── storage.py
│   │   ├── ai_client.py
│   │   └── data/
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   └── styles.css
│   ├── package.json
│   └── vite.config.ts
├── serve-public-demo.mjs
├── start-public-demo.ps1
└── README.md
```

## 本地运行

后端：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

生产构建：

```bash
cd frontend
npm install
npm run build
```

## 服务器部署说明

推荐服务器环境：

- Ubuntu 22.04
- 2 核 2G 及以上
- Nginx
- Node.js 20
- Python 3.10 及以上

部署思路：

1. 后端使用 FastAPI + Uvicorn 在 `127.0.0.1:8000` 运行。
2. 前端使用 Vite 构建为静态文件。
3. Nginx 监听 `80` 端口，静态文件指向前端 `dist`，`/api/` 反向代理到后端。
4. SQLite 数据库保存在服务器本地，后续可切换为 PostgreSQL。

## 安全说明

不要上传以下文件到 GitHub：

```text
backend/.env
backend/platform.db
backend/uploads/
backend/.venv/
frontend/node_modules/
frontend/dist/
logs/
```

`.env` 中可能包含管理员密码、AI API Key、数据库地址等敏感信息。公开仓库中只保留 `.env.example`。

## 适用场景

- 法学、社会保障、劳动法方向的课程设计或创新创业项目
- 网络主播劳动关系认定研究辅助工具
- MCN 机构用工合规初筛工具
- 新业态劳动者权益保障展示平台
- 法律科技 SaaS 产品原型

## 免责声明

本平台输出内容仅用于学习、研究和辅助分析，不构成正式法律意见。涉及具体争议处理、劳动仲裁、诉讼或合同审查时，应咨询具有执业资格的律师或相关专业机构。


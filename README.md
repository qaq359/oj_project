# OJ System - Online Judge

基于 **Python + FastAPI** 构建的在线评测系统，支持题目管理、Python 代码自动评测、用户权限管理、前端交互、数据备份恢复和代码相似度检测。

## 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| Web 框架 | FastAPI (async def) |
| ASGI 服务器 | Uvicorn |
| 数据模型 | Pydantic v2 |
| 认证 | Cookie Session (Starlette + itsdangerous) |
| 密码安全 | bcrypt |
| 持久化 | JSON 文件（原子写入） |
| 测试 | pytest (114 个用例) |
| 前端 | Streamlit |

## 快速开始

### 1. 环境要求

- Python 3.10 或以上
- pip

### 2. 安装依赖

```bash
cd oj_project
pip install -r requirements.txt
```

### 3. 启动后端

```bash
uvicorn app.main:app --reload
```

启动后访问：
- API 文档 (Swagger UI): http://localhost:8000/docs
- 健康检查: http://localhost:8000/

### 4. 启动前端（新终端）

```bash
streamlit run frontend/app.py
```

前端访问: http://localhost:8501

> 后端必须先启动，前端才能正常工作。

### 5. 运行测试

```bash
pytest                     # 全部测试
pytest -v                  # 详细输出
pytest -k "auth"           # 按关键字过滤
```

## 默认管理员账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | admin |

> 首次启动自动创建。生产环境请修改密码。

## 用户角色

| 角色 | 主要权限 |
|------|---------|
| student | 浏览题目、提交代码、查看自己提交和日志 |
| teacher | 管理题目、查看全部提交、重新评测、相似度检测 |
| admin | 管理用户（角色/禁用）、备份恢复、审计日志 |

> 注册用户默认为 student。管理员可在 Swagger UI 中通过 `PUT /api/users/{id}` 提升角色。

## 项目结构

```
oj_project/
├── app/
│   ├── main.py              # FastAPI 入口、异常处理、中间件、路由挂载
│   ├── models/
│   │   ├── enums.py         # 枚举：角色、状态、评测结果、审计动作
│   │   └── schemas.py       # Pydantic 请求/响应模型
│   ├── routers/
│   │   ├── auth.py          # 认证路由（注册/登录/登出）
│   │   ├── users.py         # 用户管理路由
│   │   ├── problems.py      # 题目路由 + 相似度检测
│   │   ├── submissions.py   # 提交路由
│   │   ├── logs.py          # 日志/审计路由
│   │   └── admin.py         # 备份恢复路由
│   ├── services/
│   │   ├── auth_service.py       # 注册/登录/登出逻辑
│   │   ├── user_service.py       # 用户管理逻辑
│   │   ├── problem_service.py    # 题目 CRUD 逻辑
│   │   ├── submission_service.py # 提交+异步评测逻辑
│   │   ├── log_service.py        # 日志查询+脱敏逻辑
│   │   ├── admin_service.py      # 备份恢复逻辑
│   │   └── similarity_service.py # 代码相似度检测
│   ├── repositories/
│   │   └── manager.py       # JSON 数据读写、原子写入、初始化
│   ├── judge/
│   │   ├── runner.py        # 子进程代码执行
│   │   ├── comparator.py    # 输出规范化比较
│   │   └── engine.py        # 评测编排+计分
│   └── utils/
│       ├── dependencies.py  # 权限依赖注入
│       └── sanitizers.py    # 日志脱敏/截断/路径隐藏
├── frontend/
│   └── app.py               # Streamlit 前端
├── tests/
│   ├── conftest.py          # 测试夹具（隔离数据、伪造Cookie）
│   ├── test_problems.py     # 23 用例
│   ├── test_judge.py        # 17 用例
│   ├── test_auth.py         # 22 用例
│   ├── test_submissions.py  # 14 用例
│   ├── test_logs.py         # 14 用例
│   ├── test_persistence.py  # 10 用例
│   └── test_similarity.py   # 14 用例
├── report/
│   └── report.md            # 实验报告
├── data/                    # 持久化数据文件
│   └── backups/             # 备份目录
├── temp/                    # 评测临时目录
├── requirements.txt
├── pytest.ini
├── .gitignore
└── README.md
```

## 持久化方式

使用 **JSON 文件** 持久化，数据文件位于 `data/` 目录：

| 文件 | 内容 |
|------|------|
| `data/users.json` | 用户数据（bcrypt 密码哈希） |
| `data/problems.json` | 题目配置（含测试点） |
| `data/submissions.json` | 提交记录 |
| `data/judge_logs.json` | 测试点级评测日志 |
| `data/audit_logs.json` | 审计日志 |
| `data/backups.json` | 备份记录索引 |
| `data/similarity_reports.json` | 相似度检测报告 |

备份文件位于 `data/backups/` 目录，每个备份包含 `manifest.json` 和全量数据副本。

## API 概览

所有业务接口统一使用 `/api` 前缀，统一响应格式：

```json
{"code": 200, "message": "ok", "data": {...}}
{"code": 404, "message": "not found", "data": null}
```

### 接口列表（共 24 个）

| 方法 | 路径 | 权限 |
|------|------|------|
| POST | /api/auth/register | 公开 |
| POST | /api/auth/login | 公开 |
| POST | /api/auth/logout | 已登录 |
| GET | /api/auth/me | 已登录 |
| GET | /api/users | admin |
| GET | /api/users/{id} | admin |
| PUT | /api/users/{id} | admin |
| GET | /api/problems | 已登录 |
| GET | /api/problems/{id} | 已登录 |
| POST | /api/problems | teacher/admin |
| PUT | /api/problems/{id} | teacher/admin |
| DELETE | /api/problems/{id} | teacher/admin |
| POST | /api/problems/{id}/similarity-check | teacher/admin |
| GET | /api/problems/{id}/similarity-reports | teacher/admin |
| POST | /api/submissions | 已登录 |
| GET | /api/submissions | 已登录 |
| GET | /api/submissions/{id} | 已登录 |
| POST | /api/submissions/{id}/rejudge | teacher/admin |
| GET | /api/submissions/{id}/logs | 已登录 |
| GET | /api/logs | teacher/admin |
| GET | /api/audit-logs | admin |
| POST | /api/admin/backups | admin |
| GET | /api/admin/backups | admin |
| POST | /api/admin/backups/{id}/restore | admin |

> 详细请求/响应格式见 http://localhost:8000/docs

## 功能模块完成情况

| 模块 | 内容 | 分值 | 状态 |
|------|------|------|------|
| Step 1 | 题目管理 | 4 | ✅ |
| Step 2 | Python 自动评测 | 4 | ✅ |
| Step 3 | 用户与权限管理 | 4 | ✅ |
| Step 4 | 提交与状态管理 | 4 | ✅ |
| Step 5 | 评测日志 | 4 | ✅ |
| Step 6 | 数据持久化、备份与恢复 | 4 | ✅ |
| Step 7 | 前端交互 | 6 | ✅ |
| Adv 3 | 代码相似度检测 | 选做 | ✅ |
| 测试 | pytest 自动化 | 5 | ✅ 114 用例 |

## 已知限制

- 基础模块仅支持 Python 语言评测
- 不强制实现 MLE（内存限制已保存但未检查）
- 评测基于子进程，非容器隔离
- 使用 JSON 文件存储，不适合高并发场景
- 备份和恢复需要管理员权限

## License

Educational project.

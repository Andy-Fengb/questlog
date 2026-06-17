# ⚔️ Quest Log v2 — 任务看板

一个基于 Flask 的个人任务管理系统，采用暗色主题看板设计。

## ✨ 特性

- **🟢 日常习惯 (Binary Habits)** — 一键打卡/撤销，带完成时间记录
- **🔵 SOP 流程 (Progressive Tasks)** — 多步骤串行任务，固定顺序锁定，逐步解锁
- **📅 打卡日志** — 按时间排序的当日记录，支持日期跳转查看历史
- **📅 历史日页** — 只读模式，支持 ◀/▶ 前后切换，预留补签标记
- **🏆 成就系统** — 国服特色成就展柜（保留自 v1）
- **📊 XP & 等级** — 经验值驱动的成长系统
- **🔒 PIN 码登录** — 多用户支持，密码哈希存储
- **🌙 暗色主题** — GitHub 风格深色 UI

## 🚀 快速开始

### Docker Compose（推荐）

```bash
git clone git@github.com:Andy-Fengb/questlog.git
cd questlog
docker compose up -d
```

访问 http://localhost:5002

### 本地开发

```bash
python3 -m venv venv
source venv/bin/activate
pip install flask gunicorn
python app.py
```

## 📂 项目结构

```
questlog/
├── app.py                  # Flask 入口
├── config.py               # 配置 & 常量
├── db.py                   # 数据库 schema & 初始化
├── utils.py                # 工具函数
├── routes/
│   ├── auth.py             # 登录/登出
│   ├── dashboard.py        # 主页看板 & 历史日页
│   ├── tasks.py            # 打卡 API (binary + SOP)
│   ├── habits.py           # 习惯 CRUD API
│   ├── status.py           # 健康检查 & 数据导出
│   └── config_routes.py    # 配置管理
├── services/
│   ├── xp_service.py       # XP 计算
│   ├── streak_service.py   # 连续天数
│   └── achievement_service.py  # 成就解锁
├── templates/
│   ├── index.html          # 今日看板
│   ├── day.html            # 历史日页
│   └── login.html          # 登录页
├── static/
│   ├── style.css           # 暗色主题样式
│   └── main.js             # 前端交互
├── Dockerfile
└── docker-compose.yml
```

## 🔌 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/login` | 登录 |
| POST | `/api/logout` | 登出 |
| POST | `/api/binary/complete` | Binary 习惯打卡 |
| POST | `/api/binary/uncomplete` | 撤销打卡 |
| POST | `/api/sop/complete_step` | SOP 完成某步 |
| GET | `/api/habits` | 获取所有习惯 |
| POST | `/api/habits` | 创建习惯 |
| PUT | `/api/habits/<id>` | 编辑习惯 |
| DELETE | `/api/habits/<id>` | 删除习惯 |
| GET | `/api/state` | 获取今日状态 |
| GET | `/api/day?date=YYYY-MM-DD` | 获取某日记录 |
| GET | `/api/export?format=json\|csv` | 导出数据 |
| GET | `/health` | 健康检查 |

## 📄 License

MIT

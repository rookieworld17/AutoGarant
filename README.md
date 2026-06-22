# AutoGarant 🤖

A production-ready Telegram bot built with a clean **MVC** architecture on top of
modern, fully asynchronous Python tooling.

## ✨ Tech stack

| Layer            | Technology                                  |
| ---------------- | ------------------------------------------- |
| Bot framework    | [aiogram 3.x](https://docs.aiogram.dev) (async) |
| Database         | PostgreSQL 16                               |
| ORM              | SQLAlchemy 2.0 (async) + asyncpg            |
| Migrations       | Alembic                                     |
| FSM / cache      | Redis 7                                     |
| Configuration    | pydantic-settings                          |
| Containerization | Docker & Docker Compose                     |

## 🏛️ Project structure (MVC)

```
AutoGarant/
├── app/
│   ├── __main__.py          # Entry point (python -m app)
│   ├── bot.py               # Bot & Dispatcher factory
│   ├── config.py            # Typed settings from .env
│   ├── controllers/         # Controller — handlers / routers
│   ├── models/              # Model — SQLAlchemy ORM models
│   ├── views/               # View — texts & keyboards
│   ├── services/            # Business logic / repositories
│   ├── middlewares/         # DB session injection, etc.
│   ├── database/            # Async engine & session factory
│   └── states/              # FSM state groups
├── migrations/              # Alembic migrations
├── docker-compose.yml       # bot + PostgreSQL + Redis
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── .env.example             # Template for environment variables
└── README.md
```

> **MVC mapping:** `models/` is the **Model**, `views/` is the **View**
> (messages & keyboards), and `controllers/` is the **Controller** (aiogram
> routers). Reusable business logic lives in `services/`.

## 🚀 Quick start with Docker (recommended)

This is the simplest way to run the whole stack (bot + database + Redis).

```bash
# 1. Clone the repository
git clone <your-repo-url> && cd AutoGarant

# 2. Create your environment file and add your BOT_TOKEN
cp .env.example .env
#   then edit .env and set BOT_TOKEN from @BotFather

# 3. Build and launch everything
docker compose up --build -d

# 4. Follow the logs
docker compose logs -f bot
```

Database migrations are applied automatically on container start
(`alembic upgrade head`).

To stop:

```bash
docker compose down          # keep data
docker compose down -v       # also remove the database volume
```

## 🛠️ Local development (without Docker)

Requires **Python 3.12+** and locally running PostgreSQL & Redis instances
(or just run them via `docker compose up -d db redis`).

```bash
# 1. Create and activate a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
#   set BOT_TOKEN, and point POSTGRES_HOST / REDIS_HOST to localhost

# 4. Apply migrations
alembic upgrade head

# 5. Run the bot
python -m app
```

## 🗄️ Database migrations

```bash
# Create a new migration after changing the models
alembic revision --autogenerate -m "add some table"

# Apply migrations
alembic upgrade head

# Roll back the last migration
alembic downgrade -1
```

## ⚙️ Configuration

All configuration is provided through environment variables. See
[`.env.example`](./.env.example) for the full list.

| Variable            | Description                                |
| ------------------- | ------------------------------------------ |
| `BOT_TOKEN`         | Telegram bot token from @BotFather         |
| `ADMIN_IDS`         | Comma-separated admin Telegram user IDs    |
| `POSTGRES_*`        | PostgreSQL connection settings             |
| `REDIS_*`           | Redis connection settings (FSM storage)    |
| `LOG_LEVEL`         | Logging level (`INFO`, `DEBUG`, …)         |

## 📦 Data model

- **users** — one row per Telegram user (identity, flags, timestamps).
- **settings** — example of a table holding mutable runtime data; use it as a
  template for the project's other dynamic tables.

## 📄 License

Proprietary — developed for the client. All rights reserved.

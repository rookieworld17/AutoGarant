# AutoGarant 🤝

**AutoGarant** — Telegram-бот эскроу-гаранта для безопасных P2P-сделок. Покупатель
вносит деньги, бот удерживает их в эскроу, а продавец получает выплату только после
подтверждения. Встроены крипто-кошелёк (пополнение/вывод через CryptoBot), система
споров с арбитражем администратора и автоматический сбор комиссий.

Построен на чистой **MVC**-архитектуре поверх асинхронного Python-стека.

---

## 📑 Содержание

- [Возможности](#-возможности)
- [Технологический стек](#-технологический-стек)
- [Структура проекта (MVC)](#-структура-проекта-mvc)
- [Быстрый старт (Docker)](#-быстрый-старт-docker-рекомендуется)
- [Локальная разработка](#-локальная-разработка-без-docker)
- [Конфигурация (.env)](#-конфигурация-env)
- [Модель данных](#-модель-данных)
- [Бизнес-логика и потоки](#-бизнес-логика-и-потоки)
- [Интеграции](#-интеграции)
- [Миграции БД](#-миграции-бд)
- [Соглашения по коду](#-соглашения-по-коду)
- [Лицензия](#-лицензия)

---

## ✨ Возможности

| Раздел | Что делает |
| ------ | ---------- |
| 🤝 **АвтоГарант** | Создание эскроу-сделки. Создавать может **и покупатель, и продавец**. Партнёр вступает по deep-link `?start=deal_<token>`. |
| 💸 **Кошелёк** | Пополнение и вывод USDT через CryptoBot. Баланс хранится в БД, отображается в USD и RUB (курс ЦБ РФ). |
| 🔍 **Поиск** | Поиск пользователя по `@username`, числовому id или ссылке `t.me/...` — рендерит карточку профиля. |
| 👤 **Профиль** | Карточка пользователя + «Мои сделки» с пагинацией (роль определяется автоматически). |
| ⚖️ **Споры** | Любая сторона эскроу-сделки может открыть спор; администратор решает в пользу покупателя (возврат) или продавца (выплата). |
| 🛠️ **Админ-панель** | `/admin` — сводка накопленных комиссий и кнопка «Вывести комиссию» (перевод администратору через CryptoBot). |

Ключевые принципы UX:

- **Одно сообщение-меню** — интерфейс редактируется на месте (`edit_text`), а не плодит
  новые сообщения.
- **MarkdownV2** — все динамические значения экранируются через `texts.escape()`.
- **Restart-safe** — FSM-состояния хранятся в Redis, срок жизни сделок — в БД
  (`deals.expires_at`); фоновый свипер закрывает просроченные сделки даже после
  перезапуска бота.

---

## 🧰 Технологический стек

| Слой | Технология |
| ---- | ---------- |
| Bot framework | [aiogram 3.x](https://docs.aiogram.dev) (async) |
| База данных | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 (async) + asyncpg |
| Миграции | Alembic |
| FSM / cache | Redis 7 |
| Конфигурация | pydantic-settings |
| Платежи | Crypto Pay API (CryptoBot) |
| Курс валют | cbr-xml-daily.ru (ЦБ РФ) |
| Контейнеризация | Docker & Docker Compose |

Требуется **Python 3.12+**.

---

## 🏛️ Структура проекта (MVC)

```
AutoGarant/
├── app/
│   ├── __main__.py          # Точка входа (python -m app): логирование, polling, свипер
│   ├── bot.py               # Фабрика Bot и Dispatcher (Redis FSM, middlewares, роутеры)
│   ├── config.py            # Типизированные настройки из .env (pydantic-settings)
│   ├── controllers/         # Controller — aiogram-роутеры (хендлеры)
│   │   ├── start.py         #   Главное меню, сделки, кошелёк, поиск, споры
│   │   ├── admin.py         #   /admin — панель и вывод комиссий
│   │   └── common.py        #   Fallback-хендлер (включается последним)
│   ├── models/              # Model — ORM-модели SQLAlchemy
│   │   ├── base.py          #   DeclarativeBase + миксины (Timestamp, IntPK)
│   │   ├── user.py          #   users
│   │   ├── deal.py          #   deals
│   │   ├── transaction.py   #   transactions (депозиты/выводы)
│   │   ├── payout.py        #   payouts (выплаты комиссий)
│   │   └── setting.py       #   settings (пример таблицы рантайм-данных)
│   ├── views/               # View — тексты и клавиатуры
│   │   ├── texts.py         #   Шаблоны сообщений + escape() для MarkdownV2
│   │   └── keyboards.py     #   Inline-клавиатуры
│   ├── services/            # Бизнес-логика / репозитории
│   │   ├── user_service.py
│   │   ├── deal_service.py
│   │   ├── transaction_service.py
│   │   ├── payout_service.py
│   │   ├── crypto_pay.py    #   Клиент Crypto Pay API (CryptoBot)
│   │   └── currency.py      #   Курс USD/RUB (ЦБ РФ, кэш 1 ч)
│   ├── middlewares/         # Инъекция DB-сессии в каждый апдейт
│   ├── database/            # Async engine + session factory
│   └── states/              # FSM-группы (WalletStates, DealStates, SearchStates)
├── migrations/              # Alembic-миграции
├── docker-compose.yml       # bot + PostgreSQL + Redis
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── .env.example             # Шаблон переменных окружения
└── README.md
```

> **MVC-маппинг:** `models/` — **Model**, `views/` — **View** (тексты и клавиатуры),
> `controllers/` — **Controller** (aiogram-роутеры). Переиспользуемая бизнес-логика
> живёт в `services/`.

---

## 🚀 Быстрый старт (Docker, рекомендуется)

Самый простой способ поднять весь стек (бот + БД + Redis).

```bash
# 1. Клонировать репозиторий
git clone <your-repo-url> && cd AutoGarant

# 2. Создать .env и заполнить значения (минимум BOT_TOKEN и CRYPTO_PAY_TOKEN)
cp .env.example .env

# 3. Собрать и запустить
docker compose up --build -d

# 4. Логи бота
docker compose logs -f bot
```

Миграции применяются автоматически при старте контейнера (`alembic upgrade head`).

Остановка:

```bash
docker compose down          # сохранить данные
docker compose down -v       # удалить и том БД
```

---

## 🛠️ Локальная разработка (без Docker)

Нужны **Python 3.12+** и запущенные PostgreSQL и Redis
(или поднимите их через `docker compose up -d db redis`).

```bash
# 1. Виртуальное окружение
python3.12 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate

# 2. Зависимости
pip install -r requirements.txt

# 3. Конфигурация: укажите POSTGRES_HOST / REDIS_HOST = localhost
cp .env.example .env

# 4. Миграции
alembic upgrade head

# 5. Запуск
python -m app
```

> ⚠️ В Docker хост БД — `db` (имя сервиса), но с хост-машины это имя не резолвится.
> Для локального запуска / выполнения миграций с хоста используйте `localhost`.

---

## ⚙️ Конфигурация (.env)

Вся конфигурация — через переменные окружения. Полный список — в
[`.env.example`](./.env.example).

| Переменная | Описание |
| ---------- | -------- |
| `BOT_TOKEN` | Токен бота от @BotFather |
| `ADMIN_IDS` | Telegram-id админов через запятую |
| `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Подключение к PostgreSQL |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_DB` | Подключение к Redis (хранилище FSM) |
| `DEPOSIT_COMMISSION_PERCENT` | Комиссия за пополнение, % |
| `WITHDRAW_COMMISSION_PERCENT` | Комиссия за вывод, % (удерживается из выплаты) |
| `COMMISSION_TG_ID` | Telegram-id получателя комиссий; пусто → первый из `ADMIN_IDS` |
| `CRYPTO_PAY_TOKEN` | Токен Crypto Pay API (CryptoBot) |
| `CRYPTO_PAY_TESTNET` | `true` → testnet (@CryptoTestnetBot), `false` → mainnet |
| `LOG_LEVEL` | Уровень логирования (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

> 🔐 Пароль PostgreSQL может содержать спецсимволы (`%`, `)`, `@`): URL подключения
> собирается через `URL.create`, поэтому ручное экранирование не нужно
> (см. `Settings.database_url`).

---

## 🗄️ Модель данных

| Таблица | Назначение |
| ------- | ---------- |
| **users** | Один пользователь Telegram. Хранит `tg_id`, публичный 7-значный `app_id`, `username`, имя и баланс `deposit` (USD). |
| **deals** | Эскроу-сделка между владельцем и партнёром. 4-значный `number`, `token` для deep-link, `owner_role` (`buyer`/`seller`), `amount`, `terms`, `status`, `expires_at`. |
| **transactions** | По одной строке на завершённую операцию кошелька. `kind` = `deposit` \| `withdraw`, сумма, комиссия и флаг `commission_paid`. |
| **payouts** | По одной строке на фактический вывод накопленной комиссии администратору. |
| **settings** | Пример таблицы изменяемых рантайм-данных (шаблон для будущих справочников). |

### Жизненный цикл сделки (`deals.status`)

```
active ──accept──> accepted ──pay──> escrow ──receipt──> completed
  │                   │                 │
  │ (TTL)             │ cancel-request  │ cancel-request → escrow_cancel
  ▼                   ▼                 ▼
expired           cancelling          dispute ──resolve──> completed (продавцу)
                      │                        └─────────> cancelled  (возврат покупателю)
                      ▼
                  cancelled
```

- **active** — создана, ждёт партнёра; имеет TTL (`expires_at`), по истечении → `expired`.
- **accepted** — партнёр принял; для покупателя следующий шаг — оплата.
- **escrow** — покупатель оплатил, деньги удержаны; TTL снимается.
- **completed** — покупатель подтвердил получение, деньги выданы продавцу.
- **cancelling / escrow_cancel** — запрос на отмену ждёт согласия второй стороны
  (маркер `escrow_cancel` сохраняет факт удержания средств).
- **dispute** — открыт спор, решается администратором.
- **expired / cancelled** — терминальные состояния (при отмене из эскроу средства
  возвращаются покупателю).

---

## 🔄 Бизнес-логика и потоки

### Создание сделки
Покупатель **или** продавец задаёт сумму и условия → подтверждает → получает
deep-link `https://t.me/<bot>?start=deal_<token>` для партнёра. Партнёру назначается
противоположная роль (`OPPOSITE_ROLE`).

### Пополнение кошелька (FSM `WalletStates`)
Сумма в USD → создаётся инвойс CryptoBot (TTL 5 мин) → фоновый воркер
`_watch_invoice` поллит статус → при оплате баланс кредитуется (за вычетом комиссии),
пишется строка в `transactions`.

### Вывод (FSM `WalletStates`)
Проверка баланса → защита от повторного вывода (`_find_unclaimed_check` сверяет
неактивированные чеки) → дебет → создаётся claimable-чек CryptoBot.

### Эскроу и подтверждение
`pay` дебетует покупателя и переводит сделку в `escrow`; `complete` (подтверждение
получения) кредитует продавца. Отмена из эскроу возвращает средства покупателю.

### Споры
Любая сторона эскроу-сделки открывает спор → администратор читает карточку и решает
исход (есть кнопка «⬅️ Назад» для повторного прочтения). Решение передаёт удержанные
средства продавцу (`completed`) или возвращает покупателю (`cancelled`).

### Комиссии и выплаты
Комиссии с оплаченных пополнений и выводов накапливаются в `transactions`
(`commission_paid = False`). Админ через `/admin` → «Вывести комиссию» сметает
неоплаченные комиссии (минимум $1), переводит сумму получателю через CryptoBot и
записывает строку в `payouts` — **только** после успешного перевода.

---

## 🔌 Интеграции

- **Crypto Pay API (CryptoBot)** — `app/services/crypto_pay.py`. Минимальный async-клиент:
  `createInvoice`, `getInvoices`, `deleteInvoice`, `createCheck`, `getChecks`, `transfer`.
  Base URL переключается testnet/mainnet через `CRYPTO_PAY_TESTNET`. Переводы
  идемпотентны по `spend_id`.
- **Курс ЦБ РФ** — `app/services/currency.py`. Тянет USD/RUB с `cbr-xml-daily.ru`,
  кэширует на 1 час; при сбое отдаёт прошлое значение.

---

## 🗃️ Миграции БД

```bash
# Создать миграцию после изменения моделей
alembic revision --autogenerate -m "add some table"

# Применить
alembic upgrade head

# Откатить последнюю
alembic downgrade -1
```

URL БД в `alembic.ini` не хардкодится — он инжектится в рантайме из `app.config`
(см. `migrations/env.py`). Имена файлов миграций — с timestamp-префиксом.

---

## 🧹 Соглашения по коду

- **Архитектура MVC** — хендлеры (controllers) тонкие, бизнес-логика — в `services/`,
  доступ к Telegram-сообщениям — через `views/`.
- **Async-всё** — SQLAlchemy async, aiohttp, aiogram 3.
- **DB-сессия на апдейт** — `DatabaseMiddleware` открывает одну сессию на апдейт и
  прокидывает её хендлерам аргументом `session`.
- **Комментарии** — код самодокументируемый: строчные `#`-комментарии не используются,
  поясняющая документация живёт в docstring'ах и в этом README.
- **MarkdownV2** — динамические данные обязательно через `texts.escape()`.

---

## 📄 Лицензия

Proprietary — разработано для клиента. Все права защищены.

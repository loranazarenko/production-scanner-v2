# Production Scanner v2

Вторая версия тестового задания: фронтенд для сканирования штрих-кодов и backend на FastAPI с PostgreSQL, который реально сохраняет операции по каждому номеру.

## Чем эта версия лучше

- Есть **PostgreSQL**, хранящий продукты и операции.
- FastAPI работает в Docker-контейнере и подключается к базе через `docker-compose`.
- Структура приближена к production: отдельные сервисы `db` и `backend`, healthcheck базы, restart-политика.
- API `/api/barcodes/{barcode}` возвращает историю (последнюю операцию) по коду.
- API `/api/operations/complete` записывает новую операцию в таблицу `production_operations`.

## Структура проекта

```text
production-scanner-v2/
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── backend/
│   ├── Dockerfile
│   └── app/
│       └── main.py
├── docker-compose.yml
└── README.md
```

## Запуск (Docker-first)

1. Установить Docker Desktop / Docker Engine.
2. В корне проекта выполнить:

```bash
docker compose up --build
```

Что произойдёт:

- поднимется контейнер `db` с PostgreSQL,
- после того как база станет здоровой (healthcheck `pg_isready`),
- соберётся образ backend (FastAPI),
- поднимется контейнер `scanner_backend`.

Backend будет доступен по адресу:

- Swagger UI: <http://localhost:8000/docs>
- Health: <http://localhost:8000/api/health>

## Запуск фронтенда

Фронтенд не контейнеризован — его удобно запускать локально, чтобы работать с камерой телефона.

Вариант через встроенный HTTP-сервер:

```bash
cd frontend
python -m http.server 5500
```

После этого открыть:

- <http://localhost:5500>

### Тест телефона

1. Убедиться, что `docker compose up --build` уже выполнен и backend доступен по `http://localhost:8000`.
2. Запустить фронтенд как HTTP-сайт (`python -m http.server 5500`).
3. Открыть сайт на телефоне по IP машины, например:
   - `http://192.168.0.10:5500`
4. В `frontend/app.js` заменить:

```javascript
const API_BASE_URL = "http://localhost:8000";
```

на:

```javascript
const API_BASE_URL = "http://192.168.0.10:8000";
```

## Как это работает

### База данных

В `docker-compose.yml` описан сервис `db` на основе образа `postgres:15-alpine`.

- база: `scanner_db`
- пользователь: `scanner`
- пароль: `scanner`

Файлы базы хранятся в Docker volume `postgres_data`, чтобы данные не терялись между перезапусками контейнера.

### Backend (FastAPI)

Backend описан в `backend/app/main.py`.

- при старте (`@app.on_event("startup")`) создаёт таблицы `products` и `production_operations` через SQLAlchemy.
- использует переменную окружения `DATABASE_URL`, задаваемую в `docker-compose.yml`.
- CORS разрешён для `http://localhost:5500` и родственных ориджинов.

Работа с базой реализована через `SessionLocal` и dependency `get_db`, как рекомендует документация FastAPI+SQLAlchemy.

### API-эндпоинты

- `GET /api/health` — проверка живости сервиса.
- `GET /api/barcodes/{barcode}` —
  - ищет продукт по штрих-коду,
  - если не найден — создаёт запись,
  - возвращает список доступных операций (пока захардкоженный справочник),
  - возвращает последнюю операцию по этому продукту, если она есть.
- `POST /api/operations/complete` —
  - принимает `barcode` и `operation_code`,
  - создаёт продукт, если он ещё не существует,
  - записывает новую операцию с `performed_at` (UTC),
  - возвращает `operation_id` и время выполнения.

### Фронтенд

Фронтенд использует `html5-qrcode` для сканирования в браузере:

- `startScanner()` включает камеру, запрашивает разрешение и настраивает `qrbox` под размер экрана.
- `onScanSuccess()` вызывается при первом успешном чтении кода:
  - останавливает сканер,
  - показывает декодированный номер,
  - вызывает `GET /api/barcodes/{barcode}`,
  - показывает список доступных операций,
  - показывает последнюю операцию по данному номеру.

## Почему такой подход близок к production

- отделены **db** и **backend** как разные контейнеры.
- URL базы и CORS настраиваются через переменные окружения.
- используется SQLAlchemy и реальные таблицы, а не in-memory словари.
- Docker Compose даёт тебе единый entrypoint: `docker compose up --build` для поднятия всей системы.

Дальше можно добавлять:

- Alembic для миграций;
- auth (JWT / HttpOnly cookies);
- роли пользователей и аудит;
- отдельный сервис для отчётности.

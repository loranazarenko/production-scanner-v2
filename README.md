# Production Scanner v2

Тестовое задание: мобильное веб-приложение для сканирования штрих-кодов камерой телефона и JSON API для контроля этапов производства.

Проект разделён на frontend и backend. Frontend запускает камеру телефона, распознаёт штрих-код и получает данные изделия через API. Backend реализован на FastAPI, развёрнут на Render и хранит демо-данные в SQLite.

## Демонстрация

- Backend API: https://production-scanner-v2.onrender.com
- Health check: https://production-scanner-v2.onrender.com/api/health
- Swagger UI: https://production-scanner-v2.onrender.com/docs

Для запуска frontend на телефоне используется HTTPS-туннель ngrok, так как браузерный доступ к камере (`getUserMedia`) требует HTTPS или `localhost`.

## Возможности

- Адаптивная страница для телефона.
- Кнопка «Сканировать».
- Запрос разрешения на доступ к камере.
- Сканирование QR-кодов и распространённых форматов штрих-кодов.
- Вывод декодированного номера.
- Запрос данных изделия после сканирования.
- Получение списка доступных операций.
- Получение последней операции по изделию.
- JSON API, готовый к подключению web-клиента и будущих нативных мобильных приложений.
- Swagger/OpenAPI документация FastAPI.
- Backend, доступный через публичный HTTPS-адрес Render.

## Структура проекта

```text
production-scanner-v2/
├── frontend/
│   ├── index.html             # Мобильная страница сканера
│   ├── styles.css             # Адаптивные стили
│   └── app.js                 # Камера, распознавание и API-запросы
├── backend/
│   ├── .python-version        # Python 3.12 для Render
│   ├── requirements.txt       # Python-зависимости
│   └── app/
│       └── main.py            # FastAPI, SQLAlchemy и SQLite
├── docker-compose.yml         # Будущая Docker/PostgreSQL-конфигурация
└── README.md
```

## Технологии

| Слой | Решение |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Сканирование | html5-qrcode |
| Backend | Python, FastAPI |
| API-документация | OpenAPI / Swagger UI |
| ORM | SQLAlchemy |
| База для demo | SQLite |
| Публичный backend | Render |
| HTTPS-туннель frontend | ngrok |

## Архитектура

```text
Android / Browser
        │
        │ HTTPS
        ▼
ngrok frontend tunnel
        │
        ▼
Static frontend (HTML / CSS / JavaScript)
        │
        │ HTTPS JSON API
        ▼
Render / FastAPI
        │
        ▼
SQLite database
```

### Почему frontend использует ngrok

Браузерный API камеры `navigator.mediaDevices.getUserMedia()` работает только в secure context:

- `https://...`
- `http://localhost`

Телефон не считает локальный адрес компьютера вида `http://192.168.x.x:5500` безопасным HTTPS-origin. Поэтому для тестирования с Android frontend открывается через URL ngrok вида:

```text
https://<random-name>.ngrok-free.app
```

## Backend API

### Проверка состояния сервиса

```http
GET /api/health
```

Ответ:

```json
{
  "status": "ok"
}
```

### Получить информацию по штрих-коду

```http
GET /api/barcodes/{barcode}
```

Пример:

```http
GET /api/barcodes/1234567890123
```

Ответ:

```json
{
  "barcode": "1234567890123",
  "available_operations": [
    {
      "id": 1,
      "code": "CUT",
      "name": "Резка"
    },
    {
      "id": 2,
      "code": "WELD",
      "name": "Сварка"
    },
    {
      "id": 3,
      "code": "PACK",
      "name": "Упаковка"
    }
  ],
  "last_operation": null
}
```

Если штрих-код отсутствует, backend создаёт новую запись изделия.

### Сохранить выполненную операцию

```http
POST /api/operations/complete
Content-Type: application/json
```

Тело запроса:

```json
{
  "barcode": "1234567890123",
  "operation_code": "CUT"
}
```

Пример ответа:

```json
{
  "success": true,
  "message": "Операция сохранена",
  "operation_id": 1,
  "performed_at": "2026-08-14T10:00:00"
}
```

## Локальный запуск frontend

### Требования

- Python 3.11+.
- Google Chrome, Microsoft Edge или Samsung Internet.
- Установленный ngrok.
- Доступ в интернет для ngrok и Render API.

### Запуск

Перейти в папку frontend:

```powershell
cd frontend
```

Запустить статический сервер:

```powershell
python -m http.server 5500
```

Открыть на компьютере:

```text
http://localhost:5500
```

## Запуск на Android

### 1. Проверить адрес API

В `frontend/app.js` должен быть указан публичный Render API:

```javascript
const API_BASE_URL = "https://production-scanner-v2.onrender.com";
```

### 2. Запустить frontend

```powershell
cd frontend
python -m http.server 5500
```

### 3. Запустить HTTPS-туннель ngrok

В отдельном PowerShell-окне:

```powershell
ngrok http 5500
```

ngrok выведет строку типа:

```text
Forwarding https://some-name.ngrok-free.app -> http://localhost:5500
```

### 4. Открыть на телефоне

На Android в Chrome или Samsung Internet открыть HTTPS-адрес из ngrok:

```text
https://some-name.ngrok-free.app
```

Нажать «Сканировать» и разрешить использование камеры.

После успешного сканирования:

1. Frontend остановит камеру.
2. На странице отобразится декодированный номер.
3. Frontend вызовет Render API.
4. API вернёт доступные операции и последнюю операцию по изделию.

## Локальный запуск backend

Backend уже развёрнут на Render, поэтому для обычной демонстрации локально запускать его не нужно.

Если требуется локальная разработка backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Локальная документация API будет доступна по адресу:

```text
http://localhost:8000/docs
```

## Deploy backend на Render

Backend автоматически деплоится из ветки `main` GitHub-репозитория.

Настройки Render:

| Поле | Значение |
|---|---|
| Service Type | Web Service |
| Runtime | Python 3 |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Python Version | 3.12 |
| Plan | Free |

Python-версия определяется файлом:

```text
backend/.python-version
```

Содержимое:

```text
3.12
```

## CORS

Для demo backend временно допускает запросы с любых frontend-origin:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Это необходимо, потому что URL ngrok меняется при новом запуске туннеля.

В production после добавления cookies/JWT нужно заменить wildcard на явный список доверенных доменов:

```python
allow_origins=[
    "https://scanner.example.com"
]
```

И только после этого включать:

```python
allow_credentials=True
```

## Ограничения demo-версии

- SQLite применяется только для демонстрации логики и API.
- Render free instance может «засыпать» после простоя, поэтому первый запрос иногда занимает до минуты.
- Файловая система бесплатного Render-сервиса не предназначена для постоянного хранения SQLite-файла между redeploy/restart.
- Список операций пока захардкожен в backend.
- Пользователи, роли, авторизация и аудит пока не реализованы.

## Дальнейшее развитие

Для production-версии планируется:

- PostgreSQL как постоянное хранилище.
- Alembic для миграций схемы БД.
- Справочник операций в базе данных.
- Привязка операций к типу изделия, участку производства и рабочему месту.
- Регистрация пользователей по email.
- Хеширование паролей.
- JWT или server-side session в HttpOnly cookies.
- Роли: оператор, контролёр, технолог, администратор.
- История изменений и полный производственный аудит.
- PWA и офлайн-очередь сканирований.
- Нативные Android/iOS приложения, использующие тот же JSON API.
- CI/CD и автоматические тесты API.
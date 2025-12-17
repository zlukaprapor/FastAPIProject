# Travel Planner API - FastAPI Implementation

REST API для планування подорожей з підтримкою конкурентного доступу через optimistic locking.

## Структура проекту

```
project/
├── app/
│   ├── __init__.py
│   ├── main.py              # Точка входу FastAPI
│   ├── database.py          # Конфігурація БД
│   ├── models.py            # SQLAlchemy моделі
│   ├── schemas.py           # Pydantic схеми
│   ├── crud.py              # CRUD операції
│   └── routers/
│       ├── __init__.py
│       ├── travel_plans.py  # Роути для планів
│       └── locations.py     # Роути для локацій
├── requirements.txt
├── .env
└── README.md
```

## Встановлення

1. **Створити віртуальне оточення:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# або
venv\Scripts\activate  # Windows
```

2. **Встановити залежності:**
```bash
python.exe -m pip install --upgrade pip
pip install -r requirements.txt
```

3. **Налаштувати БД:**
```bash
CREATE DATABASE travel_planner;
CREATE USER travel WITH PASSWORD '12345678';
GRANT ALL PRIVILEGES ON DATABASE travel_planner TO travel;

GRANT ALL PRIVILEGES ON DATABASE travel_planner TO travel;
GRANT ALL ON SCHEMA public TO travel;
ALTER SCHEMA public OWNER TO travel;
```

4. **Налаштувати .env файл:**
```bash
cp .env.example .env
# Відредагувати DATABASE_URL у .env
```

## Запуск

```bash
uvicorn app.main:app --reload --port 3000
```

API буде доступне за адресою: `http://localhost:3000`

Документація: `http://localhost:3000/docs`

## Ключові рішення

### Проблема 1: Concurrent Plan Updates
**Рішення:** Optimistic locking через поле `version`

```python
# У crud.py - update_plan()
result = db.execute(
    update(models.TravelPlan)
    .where(models.TravelPlan.id == plan_id, 
           models.TravelPlan.version == old_version)
    .values(version=old_version + 1, ...)
)

if result.rowcount == 0:
    # Version conflict - повертаємо 409
    raise HTTPException(status_code=409, detail={...})
```

### Проблема 2: Sequential Location Addition
**Рішення:** Автоматичне визначення `visit_order`

```python
# У crud.py - add_location()
max_order = db.query(func.max(Location.visit_order)).filter(
    Location.travel_plan_id == plan_id
).scalar()
new_order = (max_order or 0) + 1
```

### Проблема 3: Concurrent Location Updates
**Рішення:** Стандартна UPDATE операція через SQLAlchemy ORM забезпечує атомарність на рівні БД.

## Endpoints

### Travel Plans
- `GET /api/travel-plans` - Список планів
- `POST /api/travel-plans` - Створити план
- `GET /api/travel-plans/{id}` - Отримати план з локаціями
- `PUT /api/travel-plans/{id}` - Оновити план (з version check!)
- `DELETE /api/travel-plans/{id}` - Видалити план

### Locations
- `POST /api/travel-plans/{id}/locations` - Додати локацію
- `PUT /api/locations/{id}` - Оновити локацію
- `DELETE /api/locations/{id}` - Видалити локацію

### System
- `GET /health` - Health check

## Тестування

Запустити hurl тести 
PowerShel

cd C:\Users\Oleksii\PycharmProjects\FastAPIProject
Get-ChildItem .\tests\*.hurl | ForEach-Object { hurl --variable host=http://127.0.0.1:3000 --test $_.FullName }


```

## HTTP коди відповіді

- `200` - OK (GET, PUT)
- `201` - Created (POST)
- `204` - No Content (DELETE)
- `400` - Validation Error
- `404` - Not Found
- `409` - Conflict (version mismatch)
- `500` - Internal Server Error
- `503` - Service Unavailable (health check failed)

.\hurl\hurl --test --variable host=http://localhost:3000 --verbose tests\crud.hurl
.\hurl\hurl --test --variable host=http://localhost:3000 --verbose tests\management.hurl
.\hurl\hurl --test --variable host=http://localhost:3000 --verbose tests\race-conditions.hurl
.\hurl\hurl --test --variable host=http://localhost:3000 --verbose tests\validation.hurl   

docker-compose up --build

docker-compose down -v


K6
Завдання 1:

docker compose run --rm `
   -v "${PWD}/performance-tests:/performance-tests" `
   -e BASE_URL=http://app:4567 `
   -e K6_WEB_DASHBOARD=true `
   -e K6_WEB_DASHBOARD_EXPORT=/performance-tests/reports/lab6/shard-report_smoke.html `
   k6 run /performance-tests/tests/smoke-test.js


Завдання 2:

docker compose run --rm `
   -v "${PWD}/performance-tests:/performance-tests" `
   -e BASE_URL=http://app:4567 `
   -e K6_WEB_DASHBOARD=true `
   -e K6_WEB_DASHBOARD_EXPORT=/performance-tests/reports/lab6/shard-report_crud-load.html `
   k6 run /performance-tests/tests/crud-load-test.js
   
   
Завдання 3:

docker compose run --rm `
   -v "${PWD}/performance-tests:/performance-tests" `
   -e BASE_URL=http://app:4567 `
   -e K6_WEB_DASHBOARD=true `
   -e K6_WEB_DASHBOARD_EXPORT=/performance-tests/reports/lab6/shard-report_write-heavy-load.html `
   k6 run /performance-tests/tests/write-heavy-load-test.js
   
   
Завдання 4:

docker compose run --rm `
   -v "${PWD}/performance-tests:/performance-tests" `
   -e BASE_URL=http://app:4567 `
   -e K6_WEB_DASHBOARD=true `
   -e K6_WEB_DASHBOARD_EXPORT=/performance-tests/reports/lab6/shard-report_spike.html `
   k6 run /performance-tests/tests/spike-test.js
   
   
Завдання 5:

docker compose run --rm `
   -v "${PWD}/performance-tests:/performance-tests" `
   -e BASE_URL=http://app:4567 `
   -e K6_WEB_DASHBOARD=true `
   -e K6_WEB_DASHBOARD_EXPORT=/performance-tests/reports/lab6/shard-report_read-heavy-load.html `
   k6 run /performance-tests/tests/read-heavy-load-test.js



$ MSYS_NO_PATHCONV=1 docker compose exec app python3 tools/apply_all.py /app/db/migrations/001_create_tables_postgres.sql --mapping /app/mapping.json

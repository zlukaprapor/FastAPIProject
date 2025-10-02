from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Спочатку спробуємо завантажити .env
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv не встановлено, це нормально

# Отримуємо DATABASE_URL з різних джерел
DATABASE_URL = os.getenv("DATABASE_URL")

# Якщо не знайдено в environment variables, використовуємо значення за замовчуванням
if not DATABASE_URL or DATABASE_URL == "":
    # ВАЖЛИВО: Замініть пароль на ваш реальний пароль PostgreSQL
    DATABASE_URL = "postgresql://postgres:Ur3agd026323!@localhost:5432/travel_planner"
    print("⚠ WARNING: Using hardcoded DATABASE_URL")
    print("  Consider setting DATABASE_URL environment variable for security")

# Виводимо інформацію про підключення (без пароля)
try:
    # Парсимо URL для безпечного виводу
    from urllib.parse import urlparse

    parsed = urlparse(DATABASE_URL)
    safe_url = f"{parsed.scheme}://{parsed.username}:***@{parsed.hostname}:{parsed.port}{parsed.path}"
    print(f"📊 Database: {safe_url}")
except:
    print(f"📊 Database configured")

# Створюємо engine з додатковим логуванням для відлагодження
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Встановіть True для детального SQL логування
    pool_pre_ping=True,  # Перевіряє з'єднання перед використанням
    pool_size=5,
    max_overflow=10
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Створюємо Base тут, щоб він був доступний для моделей
Base = declarative_base()


def get_db():
    """Dependency для отримання сесії бази даних"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Ініціалізація бази даних - створення всіх таблиць"""
    # Імпортуємо моделі тут, щоб Base знав про них
    from app import models

    print("Initializing database...")
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")


def check_db_connection():
    """Перевірка підключення до бази даних"""
    try:
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        print("✓ Database connection test: SUCCESS")
        return True
    except Exception as e:
        print(f"✗ Database connection test: FAILED")
        print(f"  Error: {e}")
        return False
"""
Скрипт для ініціалізації бази даних
Запуск: python init_db.py
"""

import sys
from sqlalchemy import create_engine, inspect
from app.database import Base, DATABASE_URL

from app.models import TravelPlan, Location


def init_database():
    """Створює всі таблиці в базі даних"""
    print("=" * 60)
    print("Database Initialization Script")
    print("=" * 60)

    # Перевіряємо підключення
    print(f"\n1. Connecting to database...")
    print(f"   URL: {DATABASE_URL.replace(DATABASE_URL.split('@')[0].split('//')[1], '***')}")

    try:
        engine = create_engine(DATABASE_URL, echo=True)
        connection = engine.connect()
        print("   ✓ Connection successful!")
        connection.close()
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        sys.exit(1)

    # Перевіряємо існуючі таблиці
    print("\n2. Checking existing tables...")
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if existing_tables:
        print(f"   Found tables: {existing_tables}")
        response = input("   Drop existing tables? (yes/no): ")
        if response.lower() == 'yes':
            print("   Dropping all tables...")
            Base.metadata.drop_all(bind=engine)
            print("   ✓ Tables dropped")
    else:
        print("   No existing tables found")

    # Створюємо таблиці
    print("\n3. Creating tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("   ✓ Tables created successfully!")
    except Exception as e:
        print(f"   ✗ Error creating tables: {e}")
        sys.exit(1)

    # Перевіряємо створені таблиці
    print("\n4. Verifying created tables...")
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    for table in tables:
        columns = inspector.get_columns(table)
        print(f"\n   Table: {table}")
        print(f"   Columns: {len(columns)}")
        for col in columns:
            print(f"     - {col['name']}: {col['type']}")

    print("\n" + "=" * 60)
    print("Database initialization completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    init_database()
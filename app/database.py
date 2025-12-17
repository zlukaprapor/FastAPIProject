from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json
import os
from uuid import UUID

Base = declarative_base()

# Завантажуємо mapping
MAPPING_FILE = os.getenv("MAPPING_FILE", "mapping.json")
with open(MAPPING_FILE, "r") as f:
    SHARD_MAPPING = json.load(f)

# Connection pools для кожного шарду
ENGINES = {}
SESSION_MAKERS = {}

for shard_key, db_url in SHARD_MAPPING.items():
    engine = create_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=5
    )
    ENGINES[shard_key] = engine
    SESSION_MAKERS[shard_key] = sessionmaker(autocommit=False, autoflush=False, bind=engine)

print(f"✓ Initialized {len(ENGINES)} shard connections")


def get_shard_key(plan_id: UUID) -> str:
    """Отримує ключ шарду з останнього символу UUID"""
    return str(plan_id).lower()[-1]


def get_db_for_shard(shard_key: str):
    """Повертає сесію для конкретного шарду"""
    if shard_key not in SESSION_MAKERS:
        raise ValueError(f"Invalid shard key: {shard_key}")

    session = SESSION_MAKERS[shard_key]()
    try:
        yield session
    finally:
        session.close()


def get_db_for_plan(plan_id: UUID):
    """Повертає сесію для конкретного плану"""
    shard_key = get_shard_key(plan_id)
    return get_db_for_shard(shard_key)


def get_all_dbs():
    """Повертає генератор сесій для всіх шардів"""
    sessions = []
    try:
        for shard_key in SHARD_MAPPING.keys():
            session = SESSION_MAKERS[shard_key]()
            sessions.append(session)
            yield session
    finally:
        for session in sessions:
            session.close()


def init_db():
    """Ініціалізація всіх БД"""
    from app import models
    print("Initializing all shard databases...")
    for shard_key, engine in ENGINES.items():
        print(f"  Creating tables in shard {shard_key}")
        Base.metadata.create_all(bind=engine)
    print("✓ All shards initialized!")


def check_db_connection():
    """Перевірка підключення до всіх шардів"""
    from sqlalchemy import text
    all_ok = True
    for shard_key, session_maker in SESSION_MAKERS.items():
        try:
            session = session_maker()
            session.execute(text("SELECT 1"))
            session.close()
            print(f"✓ Shard {shard_key}: OK")
        except Exception as e:
            print(f"✗ Shard {shard_key}: FAILED - {e}")
            all_ok = False
    return all_ok
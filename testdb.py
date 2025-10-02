import psycopg2
from psycopg2 import OperationalError

def check_connection():
    try:
        conn = psycopg2.connect(
            dbname="travel_planner",
            user="postgres",
            password="Ur3agd026323!",   # твій пароль
            host="localhost",
            port=5432
        )
        print("✅ Connected successfully to travel_planner DB!")
        conn.close()
    except OperationalError as e:
        print("❌ Connection failed!")
        print(e)

if __name__ == "__main__":
    check_connection()

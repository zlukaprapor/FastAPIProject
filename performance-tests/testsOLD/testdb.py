import psycopg2
from psycopg2 import OperationalError
from dotenv import load_dotenv
import os

load_dotenv()

def check_connection():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        print("✅ Connected successfully to travel_planner DB!")
        conn.close()
    except OperationalError as e:
        print("❌ Connection failed!")
        print(e)

if __name__ == "__main__":
    check_connection()

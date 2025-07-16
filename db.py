# db.py
import psycopg2
from psycopg2.extras import DictCursor
import traceback

USER = "postgres.vpjltarimjmmvtryzpgl"
PASSWORD = "13MehMet2003."
HOST = "aws-0-eu-central-1.pooler.supabase.com"
PORT = "5432"
DBNAME = "postgres"

def get_connection():
    try:
        conn = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            dbname=DBNAME
        )
        return conn
    except Exception:
        print("❌ Veritabanına bağlanılamadı:")
        traceback.print_exc()
        return None

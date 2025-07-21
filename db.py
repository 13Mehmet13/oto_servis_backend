import psycopg2
from psycopg2.extras import DictCursor

USER = "postgres.vpjltarimjmmvtryzpgl"
PASSWORD = "13MehMet2003."
HOST = "aws-0-eu-central-1.pooler.supabase.com"
PORT = "5432"
DBNAME = "postgres"

def get_conn():
    return psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME,
        cursor_factory=DictCursor  # İsteğe bağlı: sözlük gibi erişim sağlar
    )

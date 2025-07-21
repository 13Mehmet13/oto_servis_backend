import psycopg2
from psycopg2.extras import DictCursor

USER = "servis_user"
PASSWORD = "gizli123."
HOST = "localhost"
PORT = "5432"
DBNAME = "oto_servis"

def get_conn():
    return psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME,
        cursor_factory=DictCursor  # İsteğe bağlı: sözlük gibi erişim sağlar
    )

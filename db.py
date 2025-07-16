import psycopg2
import traceback
from psycopg2.extras import DictCursor  # ✅ EKLENDİ

USER = "postgres.vpjltarimjmmvtryzpgl"
PASSWORD = "13MehMet2003."
HOST = "aws-0-eu-central-1.pooler.supabase.com"
PORT = "5432"
DBNAME = "postgres"

try:
    conn = psycopg2.connect(
        user=USER, password=PASSWORD,
        host=HOST, port=PORT,
        dbname=DBNAME
    )
    cursor = conn.cursor(cursor_factory=DictCursor)  # ✅ DİKKAT! Buraya dikkat
    print("✅ Veritabanı bağlantısı başarılı!")
except Exception:
    print("❌ Veritabanına bağlanılamadı:")
    traceback.print_exc() 

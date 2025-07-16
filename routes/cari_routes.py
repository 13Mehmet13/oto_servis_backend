# routes/cari_routes.py
from flask import Blueprint, request, jsonify
from db import conn, cursor
from datetime import datetime
import traceback, json

cari_bp = Blueprint("cari", __name__)

# ─────────────────────  TÜM CARİLERİ GETİR  ─────────────────────
@cari_bp.route("/cariler", methods=["GET"])
def carileri_getir():
    try:
        cursor.execute("""
            SELECT id, ad, tip, telefon, adres
            FROM cariler
            ORDER BY ad
        """)
        return jsonify([
            dict(id=r[0], ad=r[1], tip=r[2], telefon=r[3], adres=r[4])
            for r in cursor.fetchall()
        ]), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

# ─────────────────────  TEK CARİ GETİR  ─────────────────────
@cari_bp.route("/cari/<int:cari_id>", methods=["GET"])
def tek_cari_getir(cari_id: int):
    try:
        cursor.execute("""
            SELECT id, ad, tip, telefon, adres
            FROM cariler
            WHERE id = %s
        """, (cari_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"durum": "hata", "mesaj": "Cari bulunamadı"}), 404
        return jsonify(dict(id=row[0], ad=row[1], tip=row[2], telefon=row[3], adres=row[4])), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

# ─────────────────────  CARİ EKLE  ─────────────────────
@cari_bp.route("/cari/ekle", methods=["POST"])
def cari_ekle():
    try:
        ad = request.form["ad"]
        tip = request.form["tip"]  # 'parcaci' veya 'musteri'
        tel = request.form.get("telefon")
        adr = request.form.get("adres")

        cursor.execute("""
            INSERT INTO cariler(ad, tip, telefon, adres)
            VALUES (%s,%s,%s,%s)
        """, (ad, tip, tel, adr))
        conn.commit()
        return jsonify({"durum": "başarılı"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

# ─────────────────────  ÖDEME AL / ÖDEME YAP  ─────────────────────
@cari_bp.route("/cari/hareket/ekle", methods=["POST"])
def cari_hareket_ekle():
    """
    Form verisi (x-www-form-urlencoded):
    - cari_id (zorunlu)
    - tutar (zorunlu)
    - tur: 'alacak' (ödeme al), 'borc' (ödeme yap)  (zorunlu)
    - odeme_tipi: 'nakit', 'kart', 'havale', 'çek'  (opsiyonel)
    - aciklama: metin (opsiyonel)
    - parca_listesi_json: JSON dizisi (opsiyonel)
    """
    try:
        cari_id   = request.form.get("cari_id", type=int)
        tutar     = request.form.get("tutar", type=float)
        tur       = request.form.get("tur")  # alacak / borc
        odeme_tip = request.form.get("odeme_tipi")
        aciklama  = request.form.get("aciklama", "")
        parca_js  = request.form.get("parca_listesi_json", "[]")

        if not (cari_id and tutar and tur in ("borc", "alacak")):
            return jsonify({"durum": "hata", "mesaj": "Gerekli alanlar eksik"}), 400

        cursor.execute("""
            INSERT INTO cari_hareket
            (cari_id, tarih, aciklama, tutar, tur, odeme_tipi, parca_listesi_json)
            VALUES (%s, NOW(), %s, %s, %s, %s, %s)
        """, (cari_id, aciklama, tutar, tur, odeme_tip, parca_js))
        conn.commit()
        return jsonify({"durum": "ok"}), 200
    except Exception as e:
        traceback.print_exc()
        conn.rollback()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

# ─────────────────────  HAREKETLERİ GETİR  ─────────────────────
@cari_bp.route("/cari/<int:cari_id>/hareketler", methods=["GET"])
def cari_hareketleri_getir(cari_id):
    try:
        cursor.execute("""
            SELECT id, tarih, aciklama, tutar, tur, odeme_tipi
            FROM cari_hareket
            WHERE cari_id = %s
            ORDER BY tarih DESC
        """, (cari_id,))
        rows = cursor.fetchall()
        return jsonify([
            {
                "id": r[0],
                "tarih": r[1].strftime("%d.%m.%Y %H:%M"),
                "aciklama": r[2],
                "tutar": float(r[3]),
                "tur": r[4],
                "odeme_tipi": r[5]
            } for r in rows
        ]), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

# ─────────────────────  BAKİYE HESABI  ─────────────────────
@cari_bp.route("/cari/<int:cari_id>/bakiye", methods=["GET"])
def cari_bakiye(cari_id):
    try:
        cursor.execute("""
            SELECT
              COALESCE(SUM(CASE WHEN tur='alacak' THEN tutar END),0) -
              COALESCE(SUM(CASE WHEN tur='borc'   THEN tutar END),0)
            FROM cari_hareket
            WHERE cari_id=%s
        """, (cari_id,))
        bakiye = float(cursor.fetchone()[0])
        return jsonify({"cari_id":cari_id,"bakiye":bakiye}),200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum":"hata","mesaj":str(e)}),500

# ─────────────────────  CARI RAPOR (JSON)  ─────────────────────
@cari_bp.route("/cari/<int:id>/rapor", methods=["GET"])
def firma_raporu(id):
    try:
        cursor.execute("""
            SELECT tarih, tur, tutar, COALESCE(parca_listesi_json, '[]'::jsonb)
            FROM cari_hareket
            WHERE cari_id = %s
            ORDER BY tarih
        """, (id,))
        rows = cursor.fetchall()
        return jsonify([
            {
                "tarih": r[0].strftime("%d.%m.%Y"),
                "tur": r[1],
                "tutar": float(r[2]),
                "parcalar": r[3]
            } for r in rows
        ]), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

# ─────────────────────  SERVİS SONRASI OTOMATİK BORÇ  ─────────────────────
@cari_bp.route("/cari/borc-ekle", methods=["POST"])
def cari_borc_ekle():
    """
    Servis sonunda ‘ödeme yapılmadı’ysa,
    müşteri bilgisine göre otomatik borç yazılır.
    """
    try:
        data = request.get_json()
        arac_id       = data["arac_id"]
        tutar         = data["tutar"]
        aciklama      = data.get("aciklama", "")
        parca_listesi = data.get("parca_listesi_json", [])

        # 1) Araca bağlı müşteri bilgisi
        cursor.execute("SELECT musteri_id, musteri_tipi FROM arac WHERE id = %s", (arac_id,))
        musteri_id, musteri_tipi = cursor.fetchone()

        # 2) Müşteri adı + telefon
        if musteri_tipi == 'sahis':
            cursor.execute("SELECT ad, soyad, telefon FROM musteri WHERE id = %s", (musteri_id,))
            ad, soyad, tel = cursor.fetchone()
            cari_ad = f"{ad} {soyad}"
        else:
            cursor.execute("SELECT ad, telefon FROM kurum WHERE id = %s", (musteri_id,))
            cari_ad, tel = cursor.fetchone()

        # 3) Cari kaydı kontrol et
        cursor.execute("SELECT id FROM cariler WHERE ad = %s AND tip = 'musteri'", (cari_ad,))
        cari_row = cursor.fetchone()
        if cari_row:
            cari_id = cari_row[0]
        else:
            cursor.execute("""
                INSERT INTO cariler(ad, tip, telefon)
                VALUES (%s, 'musteri', %s)
                RETURNING id
            """, (cari_ad, tel))
            cari_id = cursor.fetchone()[0]

        # 4) Borç hareketi ekle
        cursor.execute("""
            INSERT INTO cari_hareket
            (cari_id, tarih, aciklama, tutar, tur, parca_listesi_json)
            VALUES (%s, NOW(), %s, %s, 'borc', %s)
        """, (cari_id, aciklama, tutar, json.dumps(parca_listesi)))
        conn.commit()

        return jsonify({"durum": "başarılı"}), 200
    except Exception as e:
        traceback.print_exc()
        conn.rollback()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500
# ─────────────  ESKİ HAREKETLERİ SİL (örn: 6 aydan eski)  ─────────────
# 🔴 TOPLU CARI HAREKET SİL
@cari_bp.route("/cari/hareket/sil", methods=["POST"])
def toplu_hareket_sil():
    """İstemci [[ids]] listesi gönderir ve verilen id'lere ait hareketleri siler"""
    try:
        data = request.get_json()
        ids = data.get("ids", [])
        if not ids:
            return jsonify({"durum": "hata", "mesaj": "Silinecek ID listesi boş"}), 400

        cursor.execute("DELETE FROM cari_hareket WHERE id = ANY(%s)", (ids,))
        conn.commit()
        return jsonify({"durum": "başarılı"}), 200
    except Exception as e:
        traceback.print_exc()
        conn.rollback()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

# 🆕 TARİH KRİTERİ İLE TOPLU SİL (örn. eski kayıt arşiv temizliği)
@cari_bp.route("/cari/<int:cari_id>/hareketleri-sil", methods=["POST"])
def eski_hareketleri_sil(cari_id):
    """Belirtilen tarihten (dahil değil) ÖNCEKİ tüm hareketleri siler.
    İstek body: {"tarih": "YYYY-MM-DD"}
    """
    try:
        data  = request.get_json(force=True)
        tarih_str = data.get("tarih")
        if not tarih_str:
            return jsonify({"durum": "hata", "mesaj": "'tarih' alanı zorunlu"}), 400
        try:
            # yyyy-mm-dd → datetime objesine çevirip gece 23:59.59 yapmıyoruz, < operatörü yeterli
            tarih_dt = datetime.strptime(tarih_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"durum": "hata", "mesaj": "Tarih formatı YYYY-MM-DD olmalı"}), 400

        cursor.execute(
            """
            DELETE FROM cari_hareket
            WHERE cari_id = %s AND tarih < %s
            """,
            (cari_id, tarih_dt)
        )
        silinen = cursor.rowcount
        conn.commit()
        return jsonify({"durum": "başarılı", "silinen_kayit": silinen}), 200

    except Exception as e:
        traceback.print_exc()
        conn.rollback()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500


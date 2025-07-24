from flask import Blueprint, request, jsonify
from db import get_conn
import traceback

arac_bp = Blueprint("arac", __name__)

# ✅ Tüm kayıtlı araçları getir (marka adı ile birlikte)
@arac_bp.route("/araclar", methods=["GET"])
def arac_listele():
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        a.id,
                        a.plaka,
                        a.model,
                        a.km,
                        a.model_yili,
                        a.yakit_cinsi,
                        a.sasi_no,
                        m.ad AS marka,
                        CASE 
                            WHEN a.musteri_tipi = 'sahis' THEN mus.ad || ' ' || mus.soyad
                            WHEN a.musteri_tipi = 'kurum' THEN k.ad
                            ELSE 'Bilinmiyor'
                        END AS musteri_adi,
                        CASE 
                            WHEN a.musteri_tipi = 'sahis' THEN mus.telefon
                            WHEN a.musteri_tipi = 'kurum' THEN k.telefon
                            ELSE ''
                        END AS musteri_telefon,
                        a.motor,
                        a.kw
                    FROM arac a
                    LEFT JOIN marka m ON a.marka_id = m.id
                    LEFT JOIN musteri mus ON a.musteri_id = mus.id AND a.musteri_tipi = 'sahis'
                    LEFT JOIN kurum k ON a.musteri_id = k.id AND a.musteri_tipi = 'kurum'
                    ORDER BY a.id DESC
                """)
                rows = cursor.fetchall()
                araclar = []
                for row in rows:
                    araclar.append({
                        "id": row[0],
                        "plaka": row[1],
                        "model": row[2],
                        "km": row[3],
                        "model_yili": row[4],
                        "yakit_cinsi": row[5],
                        "sasi_no": row[6],
                        "marka": row[7],
                        "musteri_adi": row[8],
                        "musteri_telefon": row[9],
                        "motor": row[10],
                        "kw": row[11]
                    })
                return jsonify(araclar), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500


# ✅ Marka listesini getir
@arac_bp.route("/arac/markalar", methods=["GET"])
def get_markalar():
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, ad FROM marka ORDER BY ad ASC")
                markalar = cursor.fetchall()
                marka_listesi = [{"id": row[0], "ad": row[1]} for row in markalar]
                return jsonify(marka_listesi), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

# ✅ Yeni araç ekle
@arac_bp.route("/arac/ekle", methods=["POST"])
def arac_ekle():
    try:
        plaka = request.form["plaka"]
        model = request.form["model"]
        motor = request.form.get("motor", "")
        kw = int(request.form.get("kw", 0) or 0)
        musteri_id = int(request.form["musteri_id"])

        # ✅ musteri_tipi düzeltildi (şahıs yerine sahis yapılır)
        musteri_tipi = request.form.get("musteri_tipi", "sahis").strip().lower()
        if musteri_tipi == "şahıs":
            musteri_tipi = "sahis"
        elif musteri_tipi != "kurum":
            musteri_tipi = "sahis"  # sadece "kurum" ve "sahis" kabul edilir

        km = int(request.form.get("km", 0) or 0)
        yakit_durumu = int(request.form.get("yakit_durumu", 0) or 0)
        yakit_cinsi = request.form.get("yakit_cinsi", "")
        sasi_no = request.form.get("sasi_no", "")
        marka_id = int(request.form.get("marka_id", 0) or 0)
        model_yili = int(request.form.get("model_yili", 0) or 0)

        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO arac (
                        plaka, model, motor, kw, musteri_id, musteri_tipi,
                        km, yakit_durumu, yakit_cinsi, sasi_no, marka_id, model_yili
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        plaka, model, motor, kw, musteri_id, musteri_tipi,
                        km, yakit_durumu, yakit_cinsi, sasi_no, marka_id, model_yili
                    )
                )
                conn.commit()
        return jsonify({"durum": "başarılı", "mesaj": "Araç eklendi."}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500


# ✅ Marka detayı
@arac_bp.route("/marka/<int:id>", methods=["GET"])
def marka_detay(id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT ad FROM marka WHERE id = %s", (id,))
                row = cursor.fetchone()
                if not row:
                    return jsonify({"mesaj": "Marka bulunamadı"}), 404
                return jsonify({"ad": row[0]}), 200
    except Exception as e:
        return jsonify({"hata": str(e)}), 500

# ✅ Araç detayı
@arac_bp.route("/arac/<int:id>", methods=["GET"])
def arac_detay(id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        a.id,
                        a.plaka,
                        a.model,
                        a.motor,
                        a.kw,
                        a.km,
                        a.model_yili,
                        a.yakit_cinsi,
                        a.sasi_no,
                        m.ad AS marka,
                        CASE 
                            WHEN a.musteri_tipi = 'sahis' THEN mus.ad || ' ' || mus.soyad
                            WHEN a.musteri_tipi = 'kurum' THEN k.ad
                            ELSE 'Bilinmiyor'
                        END AS musteri_adi,
                        CASE 
                            WHEN a.musteri_tipi = 'sahis' THEN mus.telefon
                            WHEN a.musteri_tipi = 'kurum' THEN k.telefon
                            ELSE ''
                        END AS musteri_telefon
                    FROM arac a
                    LEFT JOIN marka m ON a.marka_id = m.id
                    LEFT JOIN musteri mus ON a.musteri_id = mus.id AND a.musteri_tipi = 'sahis'
                    LEFT JOIN kurum k ON a.musteri_id = k.id AND a.musteri_tipi = 'kurum'
                    WHERE a.id = %s
                """, (id,))
                row = cursor.fetchone()
                if not row:
                    return jsonify({"durum": "hata", "mesaj": "Araç bulunamadı"}), 404
                arac = {
                    "id": row[0],
                    "plaka": row[1],
                    "model": row[2],
                    "motor": row[3],
                    "kw": row[4],
                    "km": row[5],
                    "model_yili": row[6],
                    "yakit_cinsi": row[7],
                    "sasi_no": row[8],
                    "marka": row[9],
                    "musteri_adi": row[10],
                    "musteri_telefon": row[11]
                }
                return jsonify(arac), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500
@arac_bp.route("/arac/guncelle/<int:arac_id>", methods=["POST"])
def arac_guncelle(arac_id):
    try:
        data = request.get_json()
        plaka = data.get("plaka")
        marka_id = data.get("marka_id")   # ✅ burada düzeltildi
        model = data.get("model")
        model_yili = data.get("model_yili")
        motor = data.get("motor")
        kw = data.get("kw")
        km = data.get("km")
        yakit_cinsi = data.get("yakit_cinsi")
        sasi_no = data.get("sasi_no")
        yakit_durumu = data.get("yakit_durumu")

        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE arac
                    SET plaka = %s,
                        marka_id = %s,
                        model = %s,
                        model_yili = %s,
                        motor = %s,
                        kw = %s,
                        km = %s,
                        yakit_cinsi = %s,
                        sasi_no = %s,
                        yakit_durumu = %s
                    WHERE id = %s
                """, (
                    plaka, marka_id, model, model_yili, motor, kw, km, yakit_cinsi, sasi_no, yakit_durumu, arac_id
                ))
            conn.commit()
        return jsonify({"durum": "basarili"}), 200
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500



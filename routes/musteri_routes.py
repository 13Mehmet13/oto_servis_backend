from flask import Blueprint, request, jsonify
from db import get_conn
import traceback

musteri_bp = Blueprint("musteri", __name__)

# ✅ Müşteri Ekleme
@musteri_bp.route("/musteri/ekle", methods=["POST"])
def musteri_ekle():
    try:
        tipi = request.form.get("tipi", "sahis").lower()

        with get_conn() as conn:
            with conn.cursor() as cursor:
                if tipi == "sahis":
                    ad = request.form.get("ad", "").strip()
                    soyad = request.form.get("soyad", "").strip()
                    telefon = request.form.get("telefon", "").strip()

                    if not ad:
                        return jsonify({"durum": "hata", "mesaj": "Ad alanı boş olamaz."}), 400

                    cursor.execute(
                        "INSERT INTO musteri (ad, soyad, telefon) VALUES (%s, %s, %s)",
                        (ad, soyad, telefon)
                    )

                elif tipi == "kurum":
                    unvan = request.form.get("unvan", "").strip()
                    yetkili_ad = request.form.get("yetkili_ad", "").strip()
                    yetkili_soyad = request.form.get("yetkili_soyad", "").strip()
                    telefon = request.form.get("telefon", "").strip()
                    adres = request.form.get("adres", "").strip()

                    if not unvan:
                        return jsonify({"durum": "hata", "mesaj": "Unvan (ad) alanı boş olamaz."}), 400

                    cursor.execute(
                        """
                        INSERT INTO kurum (ad, adres, telefon, "Yetkili Ad", "Yetkili Soyad")
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (unvan, adres, telefon, yetkili_ad, yetkili_soyad)
                    )

                else:
                    return jsonify({"durum": "hata", "mesaj": "Geçersiz müşteri tipi (sahis/kurum)"}), 400

                conn.commit()

        return jsonify({"durum": "başarılı", "mesaj": f"{tipi.capitalize()} müşteri başarıyla eklendi."}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500


# ✅ Müşteri Listeleme (detaylı hale getirildi)
@musteri_bp.route("/musteriler", methods=["GET"])
def musteri_listesi():
    try:
        sahiplik_raw = request.args.get("sahiplik", "").strip().lower()
        sahiplik = sahiplik_raw.replace("ş", "s").replace("ı", "i")  # şahıs → sahis

        with get_conn() as conn:
            with conn.cursor() as cursor:
                if sahiplik == "sahis":
                    cursor.execute("""
                        SELECT id, ad, soyad, telefon FROM musteri ORDER BY id DESC
                    """)
                    rows = cursor.fetchall()
                    musteriler = [{
                        "id": r[0],
                        "ad": r[1],
                        "soyad": r[2],
                        "telefon": r[3]
                    } for r in rows]

                elif sahiplik == "kurum":
                    cursor.execute("""
                        SELECT id, ad, adres, telefon, "Yetkili Ad", "Yetkili Soyad" FROM kurum ORDER BY id DESC
                    """)
                    rows = cursor.fetchall()
                    musteriler = [{
                        "id": r[0],
                        "unvan": r[1],
                        "adres": r[2],
                        "telefon": r[3],
                        "yetkili_ad": r[4],
                        "yetkili_soyad": r[5]
                    } for r in rows]

                else:
                    return jsonify({
                        "durum": "hata",
                        "mesaj": f"Geçersiz sahiplik tipi: {sahiplik_raw}"
                    }), 400

                return jsonify(musteriler), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": "Sunucu hatası: " + str(e)}), 500


# 🔧 Detaylı Listeleme (ayrıca kullanmak istersen)
@musteri_bp.route("/musteriler/<string:tip>", methods=["GET"])
def musterileri_detayli_getir(tip):
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                if tip.lower() == 'sahis':
                    cursor.execute("""
                        SELECT id, ad, soyad, telefon
                        FROM musteri
                        ORDER BY id DESC
                    """)
                    rows = cursor.fetchall()
                    return jsonify([
                        {
                            "id": r[0],
                            "ad": r[1],
                            "soyad": r[2],
                            "telefon": r[3]
                        } for r in rows
                    ])

                elif tip.lower() == 'kurum':
                    cursor.execute("""
                        SELECT id, ad, adres, telefon, "Yetkili Ad", "Yetkili Soyad"
                        FROM kurum
                        ORDER BY id DESC
                    """)
                    rows = cursor.fetchall()
                    return jsonify([
                        {
                            "id": r[0],
                            "unvan": r[1],
                            "adres": r[2],
                            "telefon": r[3],
                            "yetkili_ad": r[4],
                            "yetkili_soyad": r[5],
                        } for r in rows
                    ])

                else:
                    return jsonify({"hata": "Geçersiz müşteri tipi."}), 400

    except Exception as e:
        return jsonify({"hata": str(e)}), 500

# Şahıs Sil
from flask import Blueprint, request, jsonify
from db import get_conn

musteri_bp = Blueprint("musteri_bp", __name__)

# ─────────────── ŞAHIS SİL ───────────────
@musteri_bp.route("/musteri/sil/<int:id>", methods=["DELETE"])
def musteri_sil(id):
    conn, cursor = get_conn()
    try:
        cursor.execute("DELETE FROM musteri WHERE id = %s", (id,))
        conn.commit()
        return jsonify({"durum": "ok"})
    except Exception as e:
        conn.rollback()
        return jsonify({"hata": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# ─────────────── KURUM SİL ───────────────
@musteri_bp.route("/kurum/sil/<int:id>", methods=["DELETE"])
def kurum_sil(id):
    conn, cursor = get_conn()
    try:
        cursor.execute("DELETE FROM kurum WHERE id = %s", (id,))
        conn.commit()
        return jsonify({"durum": "ok"})
    except Exception as e:
        conn.rollback()
        return jsonify({"hata": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# ─────────────── ŞAHIS GÜNCELLE ───────────────
@musteri_bp.route("/musteri/guncelle/<int:id>", methods=["POST"])
def musteri_guncelle(id):
    data = request.json
    conn, cursor = get_conn()
    try:
        cursor.execute("""
            UPDATE musteri
            SET ad = %s, soyad = %s, telefon = %s
            WHERE id = %s
        """, (data["ad"], data["soyad"], data["telefon"], id))
        conn.commit()
        return jsonify({"durum": "ok"})
    except Exception as e:
        conn.rollback()
        return jsonify({"hata": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# ─────────────── KURUM GÜNCELLE ───────────────
@musteri_bp.route("/kurum/guncelle/<int:id>", methods=["POST"])
def kurum_guncelle(id):
    data = request.json
    conn, cursor = get_conn()
    try:
        cursor.execute("""
            UPDATE kurum
            SET ad = %s, telefon = %s, adres = %s, "Yetkili Ad" = %s, "Yetkili Soyad" = %s
            WHERE id = %s
        """, (data["ad"], data["telefon"], data["adres"], data["yetkili_ad"], data["yetkili_soyad"], id))
        conn.commit()
        return jsonify({"durum": "ok"})
    except Exception as e:
        conn.rollback()
        return jsonify({"hata": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

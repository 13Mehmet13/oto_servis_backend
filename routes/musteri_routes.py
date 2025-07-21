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


# ✅ Müşteri Listeleme (tip kontrolü ile)
@musteri_bp.route("/musteriler", methods=["GET"])
def musteri_listesi():
    try:
        sahiplik_raw = request.args.get("sahiplik", "").strip().lower()
        sahiplik = sahiplik_raw.replace("ş", "s").replace("ı", "i")  # şahıs → sahis

        with get_conn() as conn:
            with conn.cursor() as cursor:
                if sahiplik == "sahis":
                    cursor.execute("SELECT id, ad || ' ' || soyad AS ad FROM musteri ORDER BY id DESC")
                elif sahiplik == "kurum":
                    cursor.execute("SELECT id, ad AS ad FROM kurum ORDER BY id DESC")
                else:
                    return jsonify({
                        "durum": "hata",
                        "mesaj": f"Geçersiz sahiplik tipi: {sahiplik_raw}"
                    }), 400

                rows = cursor.fetchall()
                musteriler = [{"id": row[0], "ad": row[1]} for row in rows]
                return jsonify(musteriler), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "durum": "hata",
            "mesaj": "Sunucu hatası: " + str(e)
        }), 500

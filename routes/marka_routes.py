from flask import Blueprint, request, jsonify
from db import cursor, conn

marka_bp = Blueprint("marka", __name__)

# ✅ Marka Ekle
@marka_bp.route("/marka/ekle", methods=["POST"])
def marka_ekle():
    try:
        data = request.form or request.get_json()
        marka_adi = data.get("ad")
        if not marka_adi:
            return jsonify({"durum": "hata", "mesaj": "Marka adı gerekli"}), 400

        cursor.execute("INSERT INTO marka (ad) VALUES (%s)", (marka_adi,))
        conn.commit()
        return jsonify({"durum": "basarili", "mesaj": "Marka eklendi"}), 200
    except Exception as e:
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

# ✅ Marka Listele
@marka_bp.route("/marka/liste", methods=["GET"])
def marka_liste():
    try:
        cursor.execute("SELECT ad FROM marka ORDER BY ad ASC")
        markalar = cursor.fetchall()
        return jsonify(markalar), 200
    except Exception as e:
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

# ✅ Marka Güncelle
@marka_bp.route("/marka/guncelle", methods=["PUT"])
def marka_guncelle():
    try:
        data = request.get_json()
        eski_ad = data.get("eski_ad")
        yeni_ad = data.get("yeni_ad")

        if not eski_ad or not yeni_ad:
            return jsonify({"durum": "hata", "mesaj": "Gerekli veriler eksik"}), 400

        cursor.execute("UPDATE marka SET ad = %s WHERE ad = %s", (yeni_ad, eski_ad))
        conn.commit()
        return jsonify({"durum": "basarili", "mesaj": "Marka güncellendi"}), 200
    except Exception as e:
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

# ✅ Marka Sil
@marka_bp.route("/marka/sil", methods=["DELETE"])
def marka_sil():
    try:
        data = request.get_json()
        marka_adi = data.get("ad")
        if not marka_adi:
            return jsonify({"durum": "hata", "mesaj": "Marka adı gerekli"}), 400

        cursor.execute("DELETE FROM marka WHERE ad = %s", (marka_adi,))
        conn.commit()
        return jsonify({"durum": "basarili", "mesaj": "Marka silindi"}), 200
    except Exception as e:
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

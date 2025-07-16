from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from db import cursor, conn
import traceback

giris_bp = Blueprint("giris", __name__)

# ------------------------ GİRİŞ ----------------------------------- #
@giris_bp.route("/giris", methods=["POST"])
def giris():
    try:
        data = request.get_json()
        kullanici_adi = data.get("kullanici_adi")
        sifre = data.get("sifre")

        cursor.execute("""
            SELECT id, sifre, rol, aktif FROM kullanici
            WHERE kullanici_adi = %s
        """, (kullanici_adi,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"durum": "hata", "mesaj": "Kullanıcı bulunamadı."}), 404

        if not check_password_hash(user[1], sifre):
            return jsonify({"durum": "hata", "mesaj": "Şifre yanlış."}), 401

        if not user[3]:  # aktif mi?
            return jsonify({"durum": "hata", "mesaj": "Hesabınız henüz aktif değil. Lütfen admin onayını bekleyin."}), 403

        session["kullanici_id"] = user[0]
        session["rol"] = user[2]

        return jsonify({
            "durum": "basarili",
            "kullanici_id": user[0],
            "rol": user[2]
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": f"Giriş hatası: {str(e)}"}), 500

# ------------------------ KAYIT ----------------------------------- #
@giris_bp.route("/register", methods=["POST"])
def register():
    try:
        data = request.json
        ad = data.get("ad")
        soyad = data.get("soyad")
        kullanici_adi = data.get("kullanici_adi")
        email = data.get("email")
        sifre = data.get("sifre")

        rol = data.get("rol", "calisan")
        aktif = False

        cursor.execute("SELECT id FROM kullanici WHERE kullanici_adi = %s", (kullanici_adi,))
        if cursor.fetchone():
            return jsonify({"durum": "hata", "mesaj": "Bu kullanıcı adı zaten kayıtlı."})

        hashed_sifre = generate_password_hash(sifre)

        cursor.execute("""
            INSERT INTO kullanici (kullanici_adi, sifre, ad, soyad, email, rol, aktif)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (kullanici_adi, hashed_sifre, ad, soyad, email, rol, aktif))
        conn.commit()

        return jsonify({"durum": "basarili", "mesaj": "Kayıt başarılı. Admin onayı bekleniyor."})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)})



@giris_bp.route("/kullanicilar", methods=["GET"])
def kullanicilari_getir():
    cursor.execute("SELECT id, ad, soyad, email, kullanici_adi, rol, aktif FROM kullanici")
    rows = cursor.fetchall()
    users = [{
        "id": r[0],
        "ad": r[1],
        "soyad": r[2],
        "email": r[3],
        "kullanici_adi": r[4],
        "rol": r[5],
        "aktif": r[6]
    } for r in rows]
    return jsonify(users)

@giris_bp.route("/kullanici/onayla", methods=["POST"])
def kullanici_onayla():
    data = request.json
    kullanici_id = data.get("id")
    rol = data.get("rol", "calisan")

    cursor.execute("""
        UPDATE kullanici
        SET aktif = TRUE, rol = %s
        WHERE id = %s
    """, (rol, kullanici_id))
    conn.commit()

    return jsonify({"durum": "basarili"})

@giris_bp.route("/kullanici/rol", methods=["POST"])
def rol_degistir():
    data = request.json
    cursor.execute("""
        UPDATE kullanici SET rol = %s WHERE id = %s
    """, (data["rol"], data["id"]))
    conn.commit()
    return jsonify({"durum": "ok"})

@giris_bp.route("/kullanici/sil", methods=["POST"])
def kullanici_sil():
    data = request.json
    cursor.execute("DELETE FROM kullanici WHERE id = %s", (data["id"],))
    conn.commit()
    return jsonify({"durum": "ok"})

from werkzeug.security import generate_password_hash

@giris_bp.route("/kullanici/sifre", methods=["POST"])
def sifre_guncelle():
    data = request.json
    sifre_hashli = generate_password_hash(data["sifre"])
    cursor.execute("""
        UPDATE kullanici SET sifre = %s WHERE id = %s
    """, (sifre_hashli, data["id"]))
    conn.commit()
    return jsonify({"durum": "ok"})

@giris_bp.route("/kullanici/aktiflik", methods=["POST"])
def kullanici_aktiflik_degistir():
    try:
        data = request.json
        user_id = data.get("id")
        aktif = data.get("aktif")
        cursor.execute("UPDATE kullanici SET aktif = %s WHERE id = %s", (aktif, user_id))
        conn.commit()
        return jsonify({"durum": "ok"})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)})
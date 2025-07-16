from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash
from db import cursor, conn
import datetime

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/giris", methods=["POST"])
def login():
    data = request.json
    kullanici_adi = data.get("kullanici_adi")
    sifre = data.get("sifre")

    cursor.execute("SELECT id, sifre, rol, ad, soyad FROM kullanici WHERE kullanici_adi = %s AND aktif = TRUE", (kullanici_adi,))
    row = cursor.fetchone()

    if not row or not check_password_hash(row[1], sifre):
        return jsonify({"durum": "hata", "mesaj": "Geçersiz giriş."}), 401

    user_id, _, rol, ad, soyad = row
    expires = datetime.timedelta(days=7)
    access_token = create_access_token(identity={"id": user_id, "rol": rol, "ad": ad, "soyad": soyad}, expires_delta=expires)

    return jsonify({
        "durum": "basarili",
        "token": access_token,
        "rol": rol,
        "kullanici_id": user_id,
        "ad": ad,
        "soyad": soyad,
    })

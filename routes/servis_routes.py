from flask import Blueprint, request, jsonify, send_file
from datetime import datetime
from db import get_conn
import json
import os
from fpdf import FPDF

servis_bp = Blueprint("servis", __name__)

def create_servis_pdf(arac_id, km):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Araç ID: {arac_id} - KM: {km}", ln=True)
    os.makedirs("temp", exist_ok=True)
    file_path = f"temp/servis_{arac_id}.pdf"
    pdf.output(file_path)
    return file_path

@servis_bp.route("/servis/ekle", methods=["POST"])
def servis_ekle():
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                arac_id = int(request.form.get("arac_id"))
                km = int(request.form.get("km", 0))
                yakit = int(request.form.get("yakit", 0))
                iscilik_ucreti = float(request.form.get("iscilik_ucreti", 0))
                toplam_tutar = float(request.form.get("toplam_tutar", 0))
                sikayetler = request.form.get("sikayetler", "")
                aciklama = request.form.get("aciklama", "")
                parcalar = json.loads(request.form.get("parcalar_json", "[]"))

                cursor.execute("""
                    SELECT id, plaka, model, motor, kw, musteri_tipi, musteri_id,
                           km, yakit_cinsi, sasi_no, marka_id, model_yili, yakit_durumu
                    FROM arac WHERE id = %s
                """, (arac_id,))
                arac_row = cursor.fetchone()
                if not arac_row:
                    return jsonify({"durum": "hata", "mesaj": "Araç bulunamadı"}), 404

                arac_json = dict(zip([
                    "id", "plaka", "model", "motor", "kw", "musteri_tipi", "musteri_id",
                    "km", "yakit_cinsi", "sasi_no", "marka_id", "model_yili", "yakit_durumu"
                ], arac_row))

                cursor.execute("SELECT ad FROM marka WHERE id = %s", (arac_json["marka_id"],))
                m_row = cursor.fetchone()
                arac_json["marka"] = m_row[0] if m_row else None

                for p in parcalar:
                    if not p.get("manual") and p.get("parca_id"):
                        cursor.execute("SELECT satis_fiyati FROM parca WHERE id = %s", (p["parca_id"],))
                        fiyat = cursor.fetchone()
                        if fiyat:
                            birim_fiyat = float(fiyat[0])
                            adet = int(p.get("quantity", 1))
                            p["fiyat"] = birim_fiyat
                            p["toplam_fiyat"] = round(birim_fiyat * adet, 2)
                    elif p.get("manual"):
                        birim_fiyat = float(p.get("sellPrice", 0))
                        adet = int(p.get("quantity", 1))
                        p["fiyat"] = birim_fiyat
                        p["toplam_fiyat"] = round(birim_fiyat * adet, 2)

                cursor.execute("""
                    INSERT INTO servis (arac_id, tarih, aciklama, iscilik_ucreti,
                                        toplam_tutar, sikayetler, parcalar_json, arac_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (arac_id, datetime.utcnow(), aciklama, iscilik_ucreti,
                      toplam_tutar, sikayetler, json.dumps(parcalar), json.dumps(arac_json)))
                servis_id = cursor.fetchone()[0]

                cursor.execute("UPDATE arac SET km = %s, yakit_durumu = %s WHERE id = %s", (km, yakit, arac_id))

                for p in parcalar:
                    if not p.get("manual") and p.get("parca_id"):
                        cursor.execute("UPDATE parca SET stok = stok - %s WHERE id = %s",
                                       (int(p.get("quantity", 0)), int(p["parca_id"])))

                conn.commit()
                return jsonify({"durum": "başarılı", "servis_id": servis_id}), 200

    except Exception as e:
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

@servis_bp.route("/servis/detay/<int:servis_id>", methods=["GET"])
def servis_detay(servis_id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT s.id, s.tarih, s.aciklama, s.sikayetler,
                           s.iscilik_ucreti, s.toplam_tutar,
                           s.parcalar_json::text, s.arac_json::text,
                           a.musteri_tipi, a.musteri_id
                    FROM servis s
                    JOIN arac a ON s.arac_id = a.id
                    WHERE s.id = %s
                """, (servis_id,))
                row = cursor.fetchone()
                if not row:
                    return jsonify({"durum": "hata", "mesaj": "Servis bulunamadı"}), 404

                (sid, tarih, aciklama, sikayetler, iscilik, toplam,
                 parcalar_raw, arac_raw, mus_tipi, mus_id) = row

                detail = {
                    "id": sid,
                    "tarih": tarih.isoformat(timespec="seconds"),
                    "aciklama": aciklama,
                    "sikayetler": sikayetler,
                    "iscilik_ucreti": iscilik,
                    "toplam_tutar": toplam,
                    "parcalar": json.loads(parcalar_raw or "[]"),
                    "arac_json": json.loads(arac_raw or "{}"),
                    "musteri_tipi": mus_tipi
                }

                if mus_tipi == "kurum":
                    cursor.execute("""SELECT ad, telefon, adres, \"Yetkili Ad\", \"Yetkili Soyad\"
                                      FROM kurum WHERE id=%s""", (mus_id,))
                    k = cursor.fetchone()
                    if k:
                        detail |= {"unvan": k[0], "telefon": k[1], "adres": k[2],
                                   "yetkili_ad": k[3], "yetkili_soyad": k[4]}
                else:
                    cursor.execute("SELECT ad, soyad, telefon FROM musteri WHERE id=%s", (mus_id,))
                    k = cursor.fetchone()
                    if k:
                        detail |= {"musteri_ad": k[0], "musteri_soyad": k[1],
                                   "telefon": k[2], "adres": ""}

                return jsonify(detail), 200
    except Exception as e:
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

@servis_bp.route("/servis/gecmis", methods=["GET"])
def servis_gecmis():
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT s.id, s.tarih, s.toplam_tutar, s.arac_json->>'plaka',
                           s.arac_json->>'marka', s.arac_json->>'model'
                    FROM servis s ORDER BY s.tarih DESC
                """)
                rows = cursor.fetchall()
                return jsonify([{
                    "id": r[0],
                    "tarih": r[1].isoformat(timespec="seconds"),
                    "toplam_tutar": float(r[2]),
                    "plaka": r[3],
                    "marka": r[4],
                    "model": r[5]
                } for r in rows]), 200
    except Exception as e:
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

@servis_bp.route("/servis/sil/<int:servis_id>", methods=["DELETE"])
def servis_sil(servis_id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT parcalar_json::text
                    FROM servis WHERE id = %s
                """, (servis_id,))
                rec = cursor.fetchone()
                if not rec:
                    return jsonify({"durum": "hata", "mesaj": "Servis bulunamadı"}), 404

                parcalar = json.loads(rec[0] or "[]")

                cursor.execute("DELETE FROM servis WHERE id = %s", (servis_id,))
                conn.commit()
                return jsonify({"durum": "başarılı"}), 200
    except Exception as e:
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

@servis_bp.route("/servis/pdf/indir", methods=["GET"])
def indir_servis_pdf():
    try:
        arac_id = int(request.args.get("arac_id"))
        km = int(request.args.get("km"))
        pdf_path = create_servis_pdf(arac_id, km)
        absolute_path = os.path.abspath(pdf_path)
        return send_file(absolute_path, as_attachment=False)
    except Exception as e:
        return jsonify({"durum": "hata", "mesaj": str(e)})

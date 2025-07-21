from flask import Blueprint, request, jsonify, send_file
from db import get_conn
from datetime import datetime
from fpdf import FPDF
import traceback, os, json

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
        arac_id        = int(request.form.get("arac_id"))
        km             = int(request.form.get("km", 0))
        yakit          = int(request.form.get("yakit", 0))
        iscilik_ucreti = float(request.form.get("iscilik_ucreti", 0))
        toplam_tutar   = float(request.form.get("toplam_tutar", 0))
        sikayetler     = request.form.get("sikayetler", "")
        aciklama       = request.form.get("aciklama", "")
        parcalar       = json.loads(request.form.get("parcalar_json", "[]"))

        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, plaka, model, motor, kw, musteri_tipi, musteri_id,
                           km, yakit_cinsi, sasi_no, marka_id, model_yili, yakit_durumu
                    FROM arac WHERE id = %s
                """, (arac_id,))
                arac_row = cursor.fetchone()
                if not arac_row:
                    return jsonify({"durum": "hata", "mesaj": "Araç bulunamadı"}), 404

                arac_json = dict(zip([
                    "id","plaka","model","motor","kw","musteri_tipi","musteri_id",
                    "km","yakit_cinsi","sasi_no","marka_id","model_yili","yakit_durumu"
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
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

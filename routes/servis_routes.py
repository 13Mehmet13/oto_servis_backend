from flask import Blueprint, request, jsonify, send_file
from datetime import datetime
from db import get_conn
import traceback
import json
import os
from fpdf import FPDF

servis_bp = Blueprint("servis", __name__)

def parse_iskonto_tl(value):
    try:
        if value is None or value == "":
            return 0.0
        v = str(value).replace(",", ".").strip()
        isk = float(v)
        return round(max(0, isk), 2)
    except:
        return 0.0

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
                odeme_yapilmadi = request.form.get("odeme_yapilmadi") == "true"
                iskonto_tl = parse_iskonto_tl(request.form.get("iskonto_tl"))
                iskonto_not = request.form.get("iskonto_not", "")


                # --- Araç bilgileri ---
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

                # Marka ekle
                cursor.execute("SELECT ad FROM marka WHERE id = %s", (arac_json["marka_id"],))
                m_row = cursor.fetchone()
                arac_json["marka"] = m_row[0] if m_row else None

                # Parça fiyatlarını hesapla
                for p in parcalar:
                    adet = int(p.get("quantity", 1))

                    if not p.get("manual"):  # stoktan parça
                        cursor.execute("SELECT satis_fiyati FROM parca WHERE id = %s", (p["parca_id"],))
                        f = cursor.fetchone()
                        if f:
                            p["fiyat"] = float(f[0])
                            p["toplam_fiyat"] = round(p["fiyat"] * adet, 2)
                    else:  # manuel parça
                        p["fiyat"] = float(p.get("sellPrice", 0))
                        p["toplam_fiyat"] = round(p["fiyat"] * adet, 2)
                       
                        
                toplam_tutar = max(0, toplam_tutar - iskonto_tl)


                # Servisi kaydet
                cursor.execute("""
                    INSERT INTO servis (arac_id, tarih, aciklama, iscilik_ucreti,
                    toplam_tutar, sikayetler, parcalar_json, arac_json,
                    iskonto_tl, iskonto_not)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    arac_id, datetime.utcnow(), aciklama, iscilik_ucreti,
                    toplam_tutar, sikayetler, json.dumps(parcalar), json.dumps(arac_json),
                    iskonto_tl, iskonto_not

                ))
                servis_id = cursor.fetchone()[0]

                # KM & yakıt güncelle
                cursor.execute(
                    "UPDATE arac SET km = %s, yakit_durumu = %s WHERE id = %s",
                    (km, yakit, arac_id)
                )

                # Stok düş
                for p in parcalar:
                    if not p.get("manual") and p.get("parca_id"):
                        cursor.execute(
                            "UPDATE parca SET stok = stok - %s WHERE id = %s",
                            (int(p["quantity"]), p["parca_id"])
                        )

                # --- CARİ BORCU OLUŞTURMA (servis EŞ ZAMANLI bitiriliyorsa) ---
                if aciklama == "SERVIS_BITTI" and odeme_yapilmadi:
                    musteri_tipi = arac_json["musteri_tipi"]
                    musteri_id = arac_json["musteri_id"]

                    cari_ad = None
                    telefon = None
                    tip_value = "musteri"

                    if musteri_tipi == "sahis":
                        cursor.execute(
                            "SELECT ad, soyad, telefon FROM musteri WHERE id = %s",
                            (musteri_id,)
                        )
                        m = cursor.fetchone()
                        if m:
                            cari_ad = f"{m[0]} {m[1]}"
                            telefon = m[2]

                    elif musteri_tipi == "kurum":
                        cursor.execute(
                            "SELECT unvan, telefon FROM kurum WHERE id = %s",
                            (musteri_id,)
                        )
                        m = cursor.fetchone()
                        if m:
                            cari_ad = m[0]
                            telefon = m[1]
                            tip_value = "kurum"

                    if not cari_ad:
                        cari_ad = "Bilinmeyen Müşteri"

                    # --- Servis_bitir ile birebir aynı cari oluşturma mantığı ---
                    cari_id = None

                    if telefon:
                        cursor.execute(
                            "SELECT id FROM cariler WHERE telefon = %s",
                            (telefon,)
                        )
                        r = cursor.fetchone()
                        if r:
                            cari_id = r[0]

                    if cari_id is None:
                        cursor.execute(
                            "SELECT id FROM cariler WHERE ad = %s AND tip = %s",
                            (cari_ad, tip_value)
                        )
                        r = cursor.fetchone()
                        if r:
                            cari_id = r[0]

                    if cari_id is None:
                        cursor.execute("""
                            INSERT INTO cariler (ad, tip, telefon)
                            VALUES (%s, %s, %s)
                            RETURNING id
                        """, (
                            cari_ad,
                            tip_value,
                            telefon
                        ))
                        cari_id = cursor.fetchone()[0]

                    # Cari hareketi ekle
                    cursor.execute("""
                        INSERT INTO cari_hareket
                        (cari_id, tarih, aciklama, tutar, tur, parca_listesi_json)
                        VALUES (%s, NOW(), %s, %s, 'alacak', %s)
                    """, (
                        cari_id,
                        "Servis ücreti",
                        toplam_tutar,
                        json.dumps(parcalar)
                    ))

                conn.commit()
                return jsonify({"durum": "başarılı", "servis_id": servis_id}), 200

    except Exception as e:
        traceback.print_exc()
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
                           s.iskonto_tl, s.iskonto_not,
                           a.musteri_tipi, a.musteri_id
                    FROM servis s
                    JOIN arac a ON s.arac_id = a.id
                    WHERE s.id = %s
                """, (servis_id,))
                row = cursor.fetchone()
                if not row:
                    return jsonify({"durum": "hata", "mesaj": "Servis bulunamadı"}), 404

                (sid, tarih, aciklama, sikayetler, iscilik, toplam,
                 parcalar_raw, arac_raw, iskonto_tl, iskonto_not, mus_tipi, mus_id) = row

                detail = {
                    "id": sid,
                    "tarih": tarih.isoformat(timespec="seconds"),
                    "aciklama": aciklama,
                    "sikayetler": sikayetler,
                    "iscilik_ucreti": iscilik,
                    "toplam_tutar": toplam,
                    "parcalar": json.loads(parcalar_raw or "[]"),
                    "arac_json": json.loads(arac_raw or "{}"),
                    "musteri_tipi": mus_tipi,
                    "iskonto_tl": float(iskonto_tl or 0),
                    "iskonto_not": iskonto_not or ""
                }

                if mus_tipi == "kurum":
                    cursor.execute("""SELECT ad, telefon, adres, "Yetkili Ad", "Yetkili Soyad"
                                      FROM kurum WHERE id=%s""", (mus_id,))
                    k = cursor.fetchone()
                    if k:
                        detail |= {
                            "unvan": k[0],
                            "telefon": k[1],
                            "adres": k[2],
                            "yetkili_ad": k[3],
                            "yetkili_soyad": k[4]
                        }
                else:
                    cursor.execute("SELECT ad, soyad, telefon FROM musteri WHERE id=%s", (mus_id,))
                    k = cursor.fetchone()
                    if k:
                        detail |= {
                            "musteri_ad": k[0],
                            "musteri_soyad": k[1],
                            "telefon": k[2],
                            "adres": ""
                        }

                return jsonify(detail), 200
    except Exception as e:
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

@servis_bp.route("/servis/gecmis", methods=["GET"])
def servis_gecmis():
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        s.id,
                        s.tarih,
                        s.toplam_tutar,
                        s.aciklama,
                        s.iskonto_tl,
                        s.iskonto_not,
                        s.arac_json->>'plaka',
                        s.arac_json->>'marka',
                        s.arac_json->>'model'
                    FROM servis s
                    ORDER BY s.tarih DESC
                """)
                rows = cursor.fetchall()

                return jsonify([{
                    "id": r[0],
                    "tarih": r[1].isoformat(timespec="seconds"),
                    "toplam_tutar": float(r[2]),
                    "aciklama": r[3] or "",
                    "iskonto_tl": float(r[4] or 0),
                    "iskonto_not": r[5] or "",
                    "plaka": r[6],
                    "marka": r[7],
                    "model": r[8]
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
    
@servis_bp.route("/servis/guncelle/<int:servis_id>", methods=["POST"])
def servis_guncelle(servis_id):
    try:
        data = request.get_json()
        parcalar = data.get("parcalar", [])
        iscilik_ucreti = data.get("iscilik_ucreti", 0)
        toplam_tutar = data.get("toplam_tutar", 0)
        iskonto_tl = float(data.get("iskonto_tl", 0) or 0)
        iskonto_not = data.get("iskonto_not", "")

        # ✅ İSKONTOYU TOPLAMDAN DÜŞ (negatif olmasın)
        toplam_tutar = float(toplam_tutar or 0)
        toplam_tutar = max(0, toplam_tutar - iskonto_tl)

        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM servis WHERE id = %s", (servis_id,))
                if cursor.fetchone() is None:
                    return jsonify({"durum": "hata", "mesaj": "Servis bulunamadı"}), 404

                cursor.execute("""
                    UPDATE servis
                    SET iscilik_ucreti = %s,
                        parcalar_json = %s,
                        toplam_tutar = %s,
                        iskonto_tl = %s,
                        iskonto_not = %s
                    WHERE id = %s
                """, (iscilik_ucreti, json.dumps(parcalar), toplam_tutar, iskonto_tl, iskonto_not, servis_id))

            conn.commit()
        return jsonify({"durum": "basarili"})
    except Exception as e:
        print("❌ Servis güncelleme hatası:", str(e))
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500


@servis_bp.route("/servis/aktif", methods=["GET"])
def servis_aktif():
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id, arac_id, km, yakit_durumu, iscilik_ucreti, toplam_tutar, aciklama, sikayetler, parcalar_json,
                        iskonto_tl, iskonto_not
                    FROM servis
                    WHERE aciklama = 'SERVIS_AKTIF'
                    ORDER BY id DESC
                """)
                rows = cursor.fetchall()
                servisler = []
                for row in rows:
                    servisler.append({
                        "id": row[0],
                        "arac_id": row[1],
                        "km": row[2],
                        "yakit_durumu": row[3],
                        "iscilik_ucreti": float(row[4]),
                        "toplam_tutar": float(row[5]),
                        "aciklama": row[6],
                        "sikayetler": row[7],
                        "parcalar": row[8],
                        "iskonto_tl": float(row[9] or 0),
                        "iskonto_not": row[10] or ""
                    })
        return jsonify(servisler), 200
    except Exception as e:
        print("❌ servis_aktif hatası:", e)
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500


@servis_bp.route("/servis/bitir", methods=["POST"])
def servis_bitir():
    try:
        data = request.get_json()
        servis_id = data["servis_id"]
        odeme_yapilmadi = data.get("odeme_yapilmadi", False)
        toplam_tutar = float(data.get("toplam_tutar", 0))
        parcalar = data.get("parcalar", [])

        with get_conn() as conn:
            with conn.cursor() as cursor:

                # 1) Servisi bitmiş işaretle
                cursor.execute(
                    "UPDATE servis SET aciklama = 'SERVIS_BITTI' WHERE id = %s",
                    (servis_id,)
                )

                # 2) Ödeme yoksa cari borcu oluştur
                if odeme_yapilmadi:

                    # Servisten arac_json + arac_id + iskonto al
                    cursor.execute(
                        "SELECT arac_json, arac_id, iskonto_tl FROM servis WHERE id = %s",
                        (servis_id,)
                    )
                    row = cursor.fetchone()
                    if not row:
                        return jsonify({"durum": "hata", "mesaj": "Servis bulunamadı"}), 404

                    arac_json = row[0] or {}
                    arac_id = row[1]
                    iskonto_tl = float(row[2] or 0)

                    # ✅ İSKONTOYU TOPLAMDAN DÜŞ (cariye iskontolu yaz)
                    toplam_tutar = max(0, toplam_tutar - iskonto_tl)

                    # musteri_tipi & musteri_id: önce arac_json'dan, yoksa arac tablosundan
                    musteri_tipi = arac_json.get("musteri_tipi")
                    musteri_id = arac_json.get("musteri_id")

                    if not musteri_tipi or not musteri_id:
                        cursor.execute(
                            "SELECT musteri_tipi, musteri_id FROM arac WHERE id = %s",
                            (arac_id,)
                        )
                        a = cursor.fetchone()
                        musteri_tipi, musteri_id = a[0], a[1]

                    # Müşteri/Kurum bilgileri
                    cari_ad = None
                    telefon = None
                    tip_value = "musteri"   # cariler.tip alanı

                    if musteri_tipi == "sahis":
                        cursor.execute(
                            "SELECT ad, soyad, telefon FROM musteri WHERE id = %s",
                            (musteri_id,)
                        )
                        m = cursor.fetchone()
                        if m:
                            cari_ad = f"{m[0]} {m[1]}"
                            telefon = m[2]

                    elif musteri_tipi == "kurum":
                        cursor.execute(
                            "SELECT unvan, telefon FROM kurum WHERE id = %s",
                            (musteri_id,)
                        )
                        m = cursor.fetchone()
                        if m:
                            cari_ad = m[0]
                            telefon = m[1]
                            tip_value = "kurum"

                    if not cari_ad:
                        cari_ad = "Bilinmeyen Müşteri"

                    # 3) Cari bul → yoksa yeni aç
                    cari_id = None

                    # telefon varsa telefonla ara
                    if telefon:
                        cursor.execute(
                            "SELECT id FROM cariler WHERE telefon = %s",
                            (telefon,)
                        )
                        r = cursor.fetchone()
                        if r:
                            cari_id = r[0]

                    # isim + tip ile ara
                    if cari_id is None:
                        cursor.execute(
                            "SELECT id FROM cariler WHERE ad = %s AND tip = %s",
                            (cari_ad, tip_value)
                        )
                        r = cursor.fetchone()
                        if r:
                            cari_id = r[0]

                    # hiç yoksa → yeni cari aç
                    if cari_id is None:
                        cursor.execute("""
                            INSERT INTO cariler (ad, tip, telefon)
                            VALUES (%s, %s, %s)
                            RETURNING id
                        """, (
                            cari_ad,
                            tip_value,
                            telefon
                        ))
                        cari_id = cursor.fetchone()[0]

                    # ✅ açıklamaya iskonto bilgisi (isteğe bağlı ama faydalı)
                    aciklama_cari = "Servis Borcu (bitirme)"
                    if iskonto_tl > 0:
                        aciklama_cari += f" (İskonto: -{iskonto_tl} TL)"

                    # 4) Cari hareketi ekle (müşteri bize borçlandı → ALACAK)
                    cursor.execute("""
                        INSERT INTO cari_hareket
                        (cari_id, tarih, aciklama, tutar, tur, parca_listesi_json)
                        VALUES (%s, NOW(), %s, %s, 'alacak', %s)
                    """, (
                        cari_id,
                        aciklama_cari,
                        toplam_tutar,
                        json.dumps(parcalar)
                    ))

            conn.commit()
        return jsonify({"durum": "ok"}), 200

    except Exception as e:
        print("❌ Servis bitirme hatası:", e)
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

@servis_bp.route("/servis/pdf/indir", methods=["GET"])
def indir_servis_pdf():
    try:
        arac_id = int(request.args.get("arac_id"))
        km = int(request.args.get("km"))
        
        pdf_path = create_servis_pdf(arac_id, km)
        absolute_path = os.path.abspath(pdf_path)  # 👈 Tam yol alın

        return send_file(absolute_path, as_attachment=False)  # 👈 Dosyayı aç, indirme yerine göster


    except Exception as e:
        return jsonify({"durum": "hata", "mesaj": str(e)}),

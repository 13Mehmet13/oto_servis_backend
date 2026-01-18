from flask import Blueprint, send_file, jsonify
from io import BytesIO
import json, traceback
from decimal import Decimal

from db import get_conn             # psycopg2 cursor nesneniz
from pdf_utils import CustomPDF, load_fonts   # bkz. pdf_utils.py

servis_pdf_bp = Blueprint("servis_pdf", __name__)

# ─────────────────── yardımcılar ───────────────────────
def f_float(v, d=0.0):
    try:
        if v is None:
            return d
        if isinstance(v, Decimal):
            v = float(v)
        return float(str(v).replace(",", "."))
    except Exception:
        return d

def f_int(v, d=0):
    try:
        return int(str(v).replace("%", "").strip())
    except Exception:
        return d
# ───────────────────────────────────────────────────────

@servis_pdf_bp.route("/servis/pdf/<int:servis_id>", methods=["GET"])
def servis_pdf(servis_id: int):
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        tarih,
                        iscilik_ucreti,
                        parcalar_json::text,
                        arac_json::text,
                        sikayetler,
                        iskonto_tl,
                        iskonto_not
                    FROM servis
                    WHERE id = %s
                """, (servis_id,))

                rec = cursor.fetchone()
                if not rec:
                    return jsonify({"durum": "hata", "mesaj": "Servis bulunamadı"}), 404

                (
                    tarih,
                    iscilik_raw,
                    p_json,
                    a_json,
                    sikayetler,
                    iskonto_tl,
                    iskonto_not
                ) = rec

                iscilik = float(iscilik_raw or 0)
                iskonto_tl = float(iskonto_tl or 0)
                iskonto_not = iskonto_not or ""
                parcala = json.loads(p_json or "[]")
                arac = json.loads(a_json or "{}")

                marka_ad = "-"
                if arac.get("marka_id"):
                    cursor.execute("SELECT ad FROM marka WHERE id = %s", (arac["marka_id"],))
                    m = cursor.fetchone()
                    if m:
                        marka_ad = m[0]
                arac.setdefault("marka", marka_ad)

                mus_adsoy, mus_tel = "-", "-"
                mus_id = arac.get("musteri_id")
                if mus_id:
                    cursor.execute("SELECT ad, soyad, telefon FROM musteri WHERE id = %s", (mus_id,))
                    m = cursor.fetchone()
                    if m:
                        mus_adsoy = f"{m[0]} {m[1]}"
                        mus_tel = m[2]
        # 2) PDF Kurulumu ----------------------------------------------------------
        
        pdf = CustomPDF()
        load_fonts(pdf)
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        # Başlık barı
        pdf.set_fill_color(74, 103, 153)
        pdf.set_text_color(255)
        pdf.set_font("notoSans", "B", 12)
        pdf.cell(0, 8, "ARAÇ TESLİM / KABUL FORMU", ln=True, align="C", fill=True)
        pdf.ln(2)
        pdf.set_text_color(0)
        pdf.set_font("notoSans", "", 10)

        # Kolon genişlikleri
        W = pdf.w - pdf.l_margin - pdf.r_margin
        c1, c2, c3, c4 = W * 0.20, W * 0.30, W * 0.20, W * 0.30

        def cell_row(lbl1, val1, lbl2, val2):
            pdf.set_fill_color(200, 220, 255)
            pdf.cell(c1, 8, lbl1, border=1, fill=True)
            pdf.set_fill_color(255)
            pdf.cell(c2, 8, val1, border=1)
            pdf.set_fill_color(200, 220, 255)
            pdf.cell(c3, 8, lbl2, border=1, fill=True)
            pdf.set_fill_color(255)
            pdf.cell(c4, 8, val2, border=1)
            pdf.ln()

        # 2.1 Üst bilgi satırları -------------------------------------------------
        cell_row("MÜŞTERİ", mus_adsoy, "TARİH", tarih.strftime("%d.%m.%Y %H:%M"))

        # YAKIT DURUMU barı burada
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(c1, 8, "PLAKA", border=1, fill=True)
        pdf.set_fill_color(255)
        pdf.cell(c2, 8, arac.get("plaka", "-"), border=1)

        pdf.set_fill_color(200, 220, 255)
        pdf.cell(c3, 8, "YAKIT DURUMU", border=1, fill=True)
        pdf.set_fill_color(255)
        pdf.cell(c4, 8, "", border=1)
        yak_pct = f_int(arac.get("yakit_durumu", 0))
        bar_x, bar_y = pdf.get_x() - c4, pdf.get_y()
        bar_w, bar_h = c4 - 2, 6
        pdf.set_fill_color(220)
        pdf.rect(bar_x + 1, bar_y + 1, bar_w, bar_h, style="F")
        pdf.set_fill_color(0, 102, 204)
        pdf.rect(bar_x + 1, bar_y + 1, bar_w * yak_pct / 100, bar_h, style="F")
        pdf.set_draw_color(0)
        pdf.rect(bar_x + 1, bar_y + 1, bar_w, bar_h)
        pdf.set_xy(bar_x, bar_y)
        pdf.cell(c4, 8, f"%{yak_pct}", border=0, align="C")
        pdf.ln()

        

        # 3) Araç detay satırları -----------------------------------------------
        cell_row("MARKA", marka_ad, "MODEL", arac.get("model", "-"))
        cell_row("MODEL YILI", str(arac.get("model_yili", "-")), "KM", str(arac.get("km", "-")),)
        cell_row("ŞASİ NO", arac.get("sasi_no", "-"), "YAKIT CİNSİ", arac.get("yakit_cinsi", "-"))
        cell_row("MOTOR", arac.get("motor", "-"), "KW", str(arac.get("kw", "-")))

        # 4) Müşteri Şikayetleri --------------------------------------------------
        pdf.set_font("notoSans", "B", 11)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(0, 6, "MÜŞTERİ ŞİKAYETLERİ", ln=True, fill=True, align="C", border=1)
        pdf.set_font("notoSans", "", 10)
        if sikayetler:
            for line in sikayetler.split("\n"):
                pdf.cell(0, 6, line.strip(), border=1, ln=True)
        else:
            pdf.cell(0, 6, "", border=1, ln=True)


        # 5) Parça tablosu --------------------------------------------------------
        pdf.ln(3)
        pdf.set_font("notoSans", "B", 11)
        pdf.cell(0, 8, "YAPILAN İŞLEMLER", ln=True)
        w = [80, 25, 35, 35]
        hdr = ["Parça", "Adet", "Birim", "Tutar"]
        pdf.set_font("notoSans", "B", 10)
        pdf.set_fill_color(200, 220, 255)
        for i, h in enumerate(hdr):
            pdf.cell(w[i], 6, h, border=1, align="C", fill=True)
        pdf.ln()

        pdf.set_font("notoSans", "", 10)
        total_parts = 0.0
        for p in parcala:
            ad = p.get("name") or p.get("ad") or "-"
            qty = f_int(p.get("quantity") or p.get("adet") or 1)
            unit = f_float(p.get("fiyat") or p.get("sellPrice") or 0)
            ttl = f_float(p.get("toplam_fiyat") or unit * qty)
            total_parts += ttl
            row_vals = [ad, str(qty), f"{unit:.2f}", f"{ttl:.2f}"]
            for i, val in enumerate(row_vals):
                pdf.cell(w[i], 6, val, border=1, align="R" if i > 1 else "C")
            pdf.ln()
        # İşçilik
        pdf.cell(w[0],6,"İŞÇİLİK",border=1,align="C")
        pdf.cell(w[1],6,"1",border=1,align="C")
        pdf.cell(w[2],6,f"{iscilik:.2f}",border=1,align="R")
        pdf.cell(w[3],6,f"{iscilik:.2f}",border=1,align="R")
        pdf.ln()

        # Toplam hesapları
        ara  = total_parts + iscilik
        ara_iskontolu = max(0, ara - iskonto_tl)
        kdv  = ara_iskontolu * 0.20
        genel = ara_iskontolu + kdv
        # ✅ İSKONTO satırı (Ara Toplamın üstünde)
        if iskonto_tl > 0:
            pdf.set_x(pdf.w - pdf.r_margin - 85); pdf.set_fill_color(200, 220, 255)
            pdf.cell(35, 6, "İSKONTO", border=1, align="R", fill=True)
            pdf.set_fill_color(255); pdf.cell(35, 6, f"{iskonto_tl:.2f}", border=1, align="R"); pdf.ln()
        pdf.set_x(pdf.w-pdf.r_margin-85); pdf.set_fill_color(200,220,255)
        pdf.cell(35,6,"ARA TOPLAM",border=1,align="R",fill=True)
        pdf.set_fill_color(255); pdf.cell(35,6,f"{ara:.2f}",border=1,align="R"); pdf.ln()
        pdf.set_x(pdf.w-pdf.r_margin-85); pdf.set_fill_color(200,220,255)
        pdf.cell(35,6,"KDV %20",border=1,align="R",fill=True)
        pdf.set_fill_color(255); pdf.cell(35,6,f"{kdv:.2f}",border=1,align="R"); pdf.ln()
        pdf.set_x(pdf.w-pdf.r_margin-85); pdf.set_fill_color(200,220,255)
        pdf.cell(35,6,"GENEL TOPLAM",border=1,align="R",fill=True)
        pdf.set_fill_color(255); pdf.cell(35,6,f"{genel:.2f}",border=1,align="R")

        # İmza
        pdf.ln(15); pdf.set_font("notoSans","",10)
        pdf.cell(95,6,"SERVİS YETKİLİSİ",ln=0); pdf.cell(95,6,"MÜŞTERİ - YETKİLİ",ln=1)
        pdf.cell(95,6,"Ad Soyad:",ln=0); pdf.cell(95,6,f"Ad Soyad: {mus_adsoy}",ln=1)
        pdf.cell(95,6,"İmza",ln=0);      pdf.cell(95,6,f"Telefon: {mus_tel}",ln=1)
        pdf.cell(95,6,"",ln=0);          pdf.cell(95,6,"İmza",ln=1)

        # PDF yanıt
        buf = BytesIO(pdf.output(dest="S").encode("latin-1")) 
        buf.seek(0)
        filename = f"kuzucular_{arac.get('plaka','').replace(' ','')}_{tarih.strftime('%d%m%Y')}.pdf"
        return send_file(buf, mimetype="application/pdf", download_name=filename)
    

    except Exception as err:
        traceback.print_exc()
        return jsonify({"durum":"hata","mesaj":str(err)}), 500

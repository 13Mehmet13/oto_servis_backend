from flask import Blueprint, send_file, jsonify
from datetime import datetime
from io import BytesIO
from db import cursor
from pdf_utils import CustomPDF, load_fonts
import textwrap

rapor_bp = Blueprint("rapor", __name__)

@rapor_bp.route("/rapor/aylik/pdf/<int:year>/<int:month>", methods=["GET"])
def aylik_rapor_pdf(year, month):
    try:
        start_date = datetime(year, month, 1)
        end_date = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)

        cursor.execute(
            """
            SELECT p.ad, SUM(sp.adet)
            FROM servis_parca sp
            JOIN servis s ON sp.servis_id = s.id
            JOIN parca p ON sp.parca_id = p.id
            WHERE s.tarih >= %s AND s.tarih < %s
            GROUP BY p.ad
            ORDER BY SUM(sp.adet) DESC
            """,
            (start_date, end_date)
        )
        usage = cursor.fetchall()

        suggestions = [f"{ad} az kullanıldı ({adet}); gözden geçirin." for ad, adet in usage if adet < 5]

        pdf = CustomPDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        load_fonts(pdf)
        pdf.set_font("notoSans", size=14)
        pdf.cell(0, 10, f"Aylık Parça Kullanım Raporu - {year}-{month:02d}", ln=True, align="C")
        pdf.ln(6)
        pdf.set_font("notoSans", size=12)
        pdf.cell(0, 8, "Parça Kullanım:", ln=True)

        for ad, adet in usage:
            line = f"- {ad}: {adet}"
            for l in textwrap.wrap(line, width=90):
                pdf.cell(0, 8, l, ln=True)

        pdf.ln(4)
        if suggestions:
            pdf.cell(0, 8, "\u00d6neriler:", ln=True)
            for oner in suggestions:
                for l in textwrap.wrap(f"- {oner}", width=90):
                    pdf.cell(0, 8, l, ln=True)

        buf = BytesIO(pdf.output(dest="S"))
        buf.seek(0)
        return send_file(buf, mimetype="application/pdf", download_name=f"aylik_rapor_{year}_{month:02d}.pdf")

    except Exception as e:
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500
import os
from fpdf import FPDF

DEFAULT_FONT = "notoSans"
FONT_FILE = "notoSans-regular.ttf"
LOGO_FILE = "logo.png"

class CustomPDF(FPDF):
    def header(self):
        if os.path.exists(LOGO_FILE):
            self.image(LOGO_FILE, 0, 0, 90)
        self.set_xy(120, 10)
        self.set_font(DEFAULT_FONT, "B", 12)
        self.cell(0, 6, "KUZUCULAR MARİNE", ln=True, align="R")
        self.set_font(DEFAULT_FONT, "", 9)
        self.cell(0, 5, "GEMİ YAT MAKİNA ELK. PET. ÜRÜN.", ln=True, align="R")
        self.cell(0, 5, "İTH. İHR. SAN. VE TİC. LTD. ŞTİ", ln=True, align="R")
        self.cell(0, 5, "Fatih Mah. San. Sitesi Üstü Tatvan 4.Km Tatvan / BİTLİS", ln=True, align="R")
        self.cell(0, 5, "0434 827 63 13 – 0507 864 13 19 – 0534 590 93 57", ln=True, align="R")
        self.cell(0, 5, "Tatvan V.D. | V. No. 602 050 7247 | Tic. Sicil. No. 003042", ln=True, align="R")
        self.cell(0, 5, "www.kuzucular.tr | kuzucularmarine@gmail.com", ln=True, align="R")
        self.ln(5)


def load_fonts(pdf: FPDF):
    if not os.path.exists(FONT_FILE):
        raise FileNotFoundError(f"Font dosyası bulunamadı: {FONT_FILE}")
    pdf.add_font(DEFAULT_FONT, "", FONT_FILE, uni=True)
    pdf.add_font(DEFAULT_FONT, "B", FONT_FILE, uni=True)

def draw_table_header(pdf, col_widths, headers):
    pdf.set_fill_color(220, 220, 220)
    pdf.set_font(DEFAULT_FONT, "B", 10)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(DEFAULT_FONT, "", 10)

def draw_info_table(pdf, servis):
    page_width = pdf.w - pdf.l_margin - pdf.r_margin
    col1 = page_width * 0.20
    col2 = page_width * 0.30
    col3 = page_width * 0.20
    col4 = page_width * 0.30

    rows = [
        ("MÜŞTERİ", f"{servis[15]} {servis[16] or ''}", "TARİH", servis[1].strftime('%d.%m.%Y %H:%M')),
        ("PLAKA", servis[4], "YAKIT DURUMU", servis[8] or ""),
        ("KM", str(servis[7] or ""), "YAKIT CİNSİ", servis[9] or ""),
        ("MARKA", servis[5], "MODEL", servis[6]),
        ("MODEL YILI", "", "ŞASİ NO", servis[11] or ""),
        ("TİPİ", servis[12] or "", "MOTOR GÜCÜ", servis[13] or "")
    ]

    pdf.set_font(DEFAULT_FONT, "", 10)
    for left_title, left_val, right_title, right_val in rows:
        pdf.cell(col1, 8, left_title, border=1)
        pdf.cell(col2, 8, left_val, border=1)
        pdf.cell(col3, 8, right_title, border=1)
        pdf.cell(col4, 8, right_val, border=1)
        pdf.ln()

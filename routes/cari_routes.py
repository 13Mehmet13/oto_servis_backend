from flask import Blueprint, request, jsonify
from db import get_conn
from datetime import datetime
import traceback, json

cari_bp = Blueprint("cari", __name__)

# ─────────────────────  TÜM CARİLERİ GETİR  ─────────────────────
@cari_bp.route("/cariler", methods=["GET"])
def carileri_getir():
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, ad, tip, telefon, adres
                    FROM cariler
                    ORDER BY ad
                """)
                return jsonify([
                    dict(id=r[0], ad=r[1], tip=r[2], telefon=r[3], adres=r[4])
                    for r in cursor.fetchall()
                ]), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

# ─────────────────────  TEK CARİ GETİR  ─────────────────────
@cari_bp.route("/cari/<int:cari_id>", methods=["GET"])
def tek_cari_getir(cari_id: int):
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, ad, tip, telefon, adres
                    FROM cariler
                    WHERE id = %s
                """, (cari_id,))
                row = cursor.fetchone()
                if not row:
                    return jsonify({"durum": "hata", "mesaj": "Cari bulunamadı"}), 404
                return jsonify(dict(id=row[0], ad=row[1], tip=row[2], telefon=row[3], adres=row[4])), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500


# ───────────────────── CARI EKLE ──────────────────────
@cari_bp.route("/cari/ekle", methods=["POST"])
def cari_ekle():
    try:
        # JSON içeriğini doğrudan almaya çalış
        try:
            data = request.get_json(force=True)
        except Exception:
            # Eğer JSON değilse, form üzerinden yakala (Content-Type: application/x-www-form-urlencoded)
            data = request.form.to_dict()

        ad = data.get("ad", "").strip()
        tip = data.get("tip", "").strip().lower()
        telefon = data.get("telefon", "").strip()
        adres = data.get("adres", "").strip()

        if not ad or tip not in ("parcaci", "musteri", "usta"):
            return jsonify({"durum": "hata", "mesaj": "Geçersiz veri"}), 400

        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO cariler (ad, tip, telefon, adres)
                    VALUES (%s, %s, %s, %s)
                """, (ad, tip, telefon or None, adres or None))

        return jsonify({"durum": "ok"})
    except Exception as e:
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500


# ─────────────────────  ÖDEME AL / ÖDEME YAP  ─────────────────────
@cari_bp.route("/cari/hareket/ekle", methods=["POST"])
def cari_hareket_ekle():
    try:
        cari_id   = request.form.get("cari_id", type=int)
        tutar     = request.form.get("tutar", type=float)
        tur       = request.form.get("tur")  # "alacak", "verecek", "odemeal", "odemeyap"
        odeme_tip = request.form.get("odeme_tipi")
        aciklama  = request.form.get("aciklama", "")
        parca_js  = request.form.get("parca_listesi_json", "[]")

        if not (cari_id and tutar and tur in ("alacak", "verecek", "odemeal", "odemeyap")):
            return jsonify({"durum": "hata", "mesaj": "Geçersiz veri"}), 400

        # tur değerini veritabanına uygun hale getir
        if tur == "alacak":
            veri_turu = "alacak"  # cari bana borçlandı
        elif tur == "verecek":
            veri_turu = "verecek"    # ben cariye borçlandım
        elif tur == "odemeal":
            veri_turu = "odemeal"    # adam bana ödeme yaptı, borcu azaldı
        elif tur == "odemeyap":
            veri_turu = "odemeyap"  # ben adama ödeme yaptım, benim borcum azaldı

        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO cari_hareket
                    (cari_id, tarih, aciklama, tutar, tur, odeme_tipi, parca_listesi_json)
                    VALUES (%s, NOW(), %s, %s, %s, %s, %s)
                """, (cari_id, aciklama, tutar, veri_turu, odeme_tip, parca_js))
                conn.commit()
                return jsonify({"durum": "ok"}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500


# ─────────────────────  HAREKETLERİ GETİR  ─────────────────────
@cari_bp.route("/cari/<int:cari_id>/hareketler", methods=["GET"])
def cari_hareketleri_getir(cari_id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, tarih, aciklama, tutar, tur, odeme_tipi, parca_listesi_json
                    FROM cari_hareket
                    WHERE cari_id = %s
                    ORDER BY tarih DESC
                """, (cari_id,))
                rows = cursor.fetchall()
                return jsonify([
                    {
                        "id": r[0],
                        "tarih": r[1].strftime("%d.%m.%Y %H:%M"),
                        "aciklama": r[2],
                        "tutar": float(r[3]),
                        "tur": r[4],
                        "odeme_tipi": r[5],
                        "parca_listesi_json": r[6]  # ✅ Eksik alan eklendi
                    } for r in rows
                ]), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500


# ─────────────────────  BAKİYE HESABI  ─────────────────────
@cari_bp.route("/cari/<int:cari_id>/bakiye", methods=["GET"])
def cari_bakiye(cari_id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                      COALESCE(SUM(CASE WHEN tur='alacak' THEN tutar END),0) -
                      COALESCE(SUM(CASE WHEN tur='borc'   THEN tutar END),0)
                    FROM cari_hareket
                    WHERE cari_id=%s
                """, (cari_id,))
                bakiye = float(cursor.fetchone()[0])
                return jsonify({"cari_id": cari_id, "bakiye": bakiye}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

# ─────────────────────  CARI RAPOR (JSON)  ─────────────────────
@cari_bp.route("/cari/<int:id>/rapor", methods=["GET"])
def firma_raporu(id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT tarih, tur, tutar, COALESCE(parca_listesi_json, '[]'::jsonb)
                    FROM cari_hareket
                    WHERE cari_id = %s
                    ORDER BY tarih
                """, (id,))
                rows = cursor.fetchall()
                return jsonify([
                    {
                        "tarih": r[0].strftime("%d.%m.%Y"),
                        "tur": r[1],
                        "tutar": float(r[2]),
                        "parcalar": r[3]
                    } for r in rows
                ]), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

# ─────────────────────  SERVİS SONRASI OTOMATİK BORÇ  ─────────────────────
@cari_bp.route("/cari/borc-ekle", methods=["POST"])
def cari_borc_ekle():
    try:
        data = request.get_json()
        arac_id = data["arac_id"]
        tutar = float(data["tutar"])
        aciklama = data.get("aciklama", "Servis kaydı - ödeme yapılmadı")
        parca_listesi = data.get("parca_listesi_json", [])

        with get_conn() as conn:
            with conn.cursor() as cursor:
                # Araçtan müşteri id ve tipi çek
                cursor.execute(
                    "SELECT musteri_id, musteri_tipi FROM arac WHERE id = %s",
                    (arac_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return jsonify({"durum": "hata", "mesaj": "Araç bulunamadı"}), 404

                musteri_id, musteri_tipi = row[0], row[1]

                cari_ad = None
                telefon = None
                tip_value = "musteri"  # cariler.tip

                if musteri_tipi == "sahis":
                    cursor.execute(
                        "SELECT ad, soyad, telefon FROM musteri WHERE id = %s",
                        (musteri_id,)
                    )
                    m = cursor.fetchone()
                    if m:
                        cari_ad = f"{m[0]} {m[1]}"
                        telefon = m[2]
                        tip_value = "musteri"

                elif musteri_tipi == "kurum":
                    # kurum tablon dandaki kolona göre: genelde 'unvan' + 'telefon'
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

                # --- Servis_bitir ile aynı cari bul/oluştur mantığı ---
                cari_id = None

                # 1) Telefon ile ara
                if telefon:
                    cursor.execute(
                        "SELECT id FROM cariler WHERE telefon = %s",
                        (telefon,)
                    )
                    c = cursor.fetchone()
                    if c:
                        cari_id = c[0]

                # 2) Yoksa ad + tip ile ara
                if cari_id is None:
                    cursor.execute(
                        "SELECT id FROM cariler WHERE ad = %s AND tip = %s",
                        (cari_ad, tip_value)
                    )
                    c = cursor.fetchone()
                    if c:
                        cari_id = c[0]

                # 3) Hâlâ yoksa yeni cari aç
                if cari_id is None:
                    cursor.execute("""
                        INSERT INTO cariler(ad, tip, telefon)
                        VALUES (%s, %s, %s)
                        RETURNING id
                    """, (cari_ad, tip_value, telefon))
                    cari_id = cursor.fetchone()[0]

                # 🔴 ÖNEMLİ: Artık 'borc' YOK → 'alacak' yazıyoruz
                cursor.execute("""
                    INSERT INTO cari_hareket
                        (cari_id, tarih, aciklama, tutar, tur, parca_listesi_json)
                    VALUES
                        (%s, NOW(), %s, %s, %s, %s)
                """, (
                    cari_id,
                    aciklama,
                    tutar,
                    "alacak",                  # müşteri sana borçlandı
                    json.dumps(parca_listesi)
                ))

                conn.commit()

        return jsonify({"durum": "başarılı"}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500


@cari_bp.route("/cari/hareket/sil", methods=["POST"])
def toplu_hareket_sil():
    try:
        data = request.get_json()
        ids = data.get("ids", [])
        if not ids:
            return jsonify({"durum": "hata", "mesaj": "Silinecek ID listesi boş"}), 400

        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM cari_hareket WHERE id = ANY(%s)", (ids,))
                conn.commit()
                return jsonify({"durum": "başarılı"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

@cari_bp.route("/cari/<int:cari_id>/hareketleri-sil", methods=["POST"])
def eski_hareketleri_sil(cari_id):
    try:
        data = request.get_json(force=True)
        tarih_str = data.get("tarih")
        if not tarih_str:
            return jsonify({"durum": "hata", "mesaj": "'tarih' alanı zorunlu"}), 400
        try:
            tarih_dt = datetime.strptime(tarih_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"durum": "hata", "mesaj": "Tarih formatı YYYY-MM-DD olmalı"}), 400

        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM cari_hareket
                    WHERE cari_id = %s AND tarih < %s
                    """,
                    (cari_id, tarih_dt)
                )
                silinen = cursor.rowcount
                conn.commit()
                return jsonify({"durum": "başarılı", "silinen_kayit": silinen}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

# kasa_routes.py gibi bir dosyada olabilir
@cari_bp.route("/kasa/ozet", methods=["GET"])
def kasa_ozet():
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                # Net Alacak: alacak - odemeal
                cursor.execute("""
                    SELECT
                        COALESCE(SUM(CASE WHEN tur = 'alacak' THEN tutar ELSE 0 END), 0) -
                        COALESCE(SUM(CASE WHEN tur = 'odemeal' THEN tutar ELSE 0 END), 0)
                    FROM cari_hareket
                """)
                net_alacak = cursor.fetchone()[0] or 0

                # Net Verecek: verecek - odemeyap
                cursor.execute("""
                    SELECT
                        COALESCE(SUM(CASE WHEN tur = 'verecek' THEN tutar ELSE 0 END), 0) -
                        COALESCE(SUM(CASE WHEN tur = 'odemeyap' THEN tutar ELSE 0 END), 0)
                    FROM cari_hareket
                """)
                net_verecek = cursor.fetchone()[0] or 0

                return jsonify({
                    "toplam_alacak": float(net_alacak),
                    "toplam_verecek": float(net_verecek)
                }), 200
    except Exception as e:
        print("❌ Kasa özeti hatası:", e)
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500



@cari_bp.route("/satislar", methods=["GET"])
def satislari_getir():
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT ch.id, ch.tarih, ch.tutar, ch.aciklama, c.ad, c.telefon
                    FROM cari_hareket ch
                    JOIN cariler c ON ch.cari_id = c.id
                    WHERE ch.tur = 'alacak' AND c.tip = 'musteri'
                    ORDER BY ch.tarih DESC
                """)
                rows = cursor.fetchall()
                satislar = [
                    {
                        "id": r[0],
                        "tarih": r[1].strftime("%Y-%m-%d %H:%M"),
                        "tutar": float(r[2]),
                        "aciklama": r[3],
                        "musteri_ad": r[4],
                        "telefon": r[5],
                    }
                    for r in rows
                ]
                return jsonify(satislar), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"hata": str(e)}), 500

@cari_bp.route("/cari/satis", methods=["POST"])
def cari_satis_ekle():
    try:
        data = request.json
        cari_id = data.get("cari_id")
        tutar = data.get("tutar")
        parca_listesi = data.get("parca_listesi_json", [])
        aciklama = data.get("aciklama", "Satış işlemi")

        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO cari_hareket (cari_id, tutar, tur, aciklama, parca_listesi_json)
                    VALUES (%s, %s, 'alacak', %s, %s)
                """, (cari_id, tutar, aciklama, json.dumps(parca_listesi)))
                return jsonify({"durum": "ok"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

@cari_bp.route("/kasa/hareketleri", methods=["GET"])
def kasa_hareketleri():
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        ch.id,
                        ch.tarih,
                        ch.aciklama,
                        ch.tutar,
                        ch.tur,
                        ch.odeme_tipi,
                        ch.cari_id,
                        c.ad AS cari_ad,
                        c.tip AS cari_tip,
                        c.telefon AS cari_telefon
                    FROM cari_hareket ch
                    LEFT JOIN cariler c ON ch.cari_id = c.id
                    ORDER BY ch.tarih DESC
                    LIMIT 100
                """)
                rows = cursor.fetchall()
                hareketler = []
                for row in rows:
                    hareketler.append({
                        "id": row[0],
                        "tarih": row[1].isoformat(),
                        "aciklama": row[2],
                        "tutar": float(row[3]),
                        "tur": row[4],
                        "odeme_tipi": row[5],
                        "cari_id": row[6],
                        "cari": {
                            "ad": row[7],
                            "tip": row[8],  # cariler.tip (örn: parcaci, musteri, usta)
                            "telefon": row[9]
                        } if row[7] and row[8] else None
                    })

                return jsonify(hareketler), 200

    except Exception as e:
        print("❌ kasa_hareketleri hatası:", e)
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

@cari_bp.route("/cari/guncelle/<int:id>", methods=["PUT"])
def cari_guncelle(id):
    try:
        data = request.get_json()

        ad = data.get("ad", "").strip()
        telefon = data.get("telefon", "").strip()

        if not ad or not telefon:
            return jsonify({"durum": "hata", "mesaj": "Ad ve telefon boş olamaz."}), 400

        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE cariler
                    SET ad = %s, telefon = %s
                    WHERE id = %s
                """, (ad, telefon, id))
                conn.commit()

        return jsonify({"durum": "ok", "mesaj": "Cari güncellendi."})

    except Exception as e:
        print("❌ Cari güncelleme hatası:", e)
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": "Bir hata oluştu."}), 500

@cari_bp.route("/cari/sil/<int:id>", methods=["DELETE"])
def cari_sil(id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM cariler WHERE id = %s", (id,))
                if cursor.rowcount == 0:
                    return jsonify({"durum": "hata", "mesaj": "Cari bulunamadı"}), 404
                conn.commit()
                return jsonify({"durum": "ok", "mesaj": f"{id} numaralı cari silindi"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500


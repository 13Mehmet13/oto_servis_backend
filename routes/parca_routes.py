from flask import Blueprint, request, jsonify
from db import cursor, conn
import traceback

parca_bp = Blueprint("parca", __name__)

# ────────────────────────── Yardımcı ──────────────────────────
def _g(param, default=None, cast=str):
    """
    Hem JSON hem form body'den parametre al.
    cast=float/int […] ile tip dönüştürür, hata olursa default döner.
    """
    val = (request.json or {}).get(param) or request.form.get(param) or default
    try:
        return cast(val) if val is not None else default
    except Exception:
        return default
# ───────────────────────────────────────────────────────────────


# ▶ Parça ekle
@parca_bp.route("/parca/ekle", methods=["POST"])
def parca_ekle():
    try:
        ad            = _g("ad")
        stok          = _g("stok", 0, int)
        alis_fiyati   = _g("alis_fiyati", 0.0, float)
        satis_fiyati  = _g("satis_fiyati", 0.0, float)

        if not ad:
            return jsonify({"durum": "hata", "mesaj": "Parça adı gerekli"}), 400

        cursor.execute(
            """
            INSERT INTO parca (ad, stok, alis_fiyati, satis_fiyati)
            VALUES (%s, %s, %s, %s)
            """,
            (ad, max(stok, 0), alis_fiyati, satis_fiyati)
        )
        conn.commit()
        return jsonify({"durum": "başarılı", "mesaj": "Parça eklendi"}), 200
    except Exception as e:
        traceback.print_exc()
        conn.rollback()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500


# ▶ Parçaları listele
@parca_bp.route("/parca/liste", methods=["GET"])
def parca_liste():
    try:
        cursor.execute("""
            SELECT id, ad, stok, alis_fiyati, satis_fiyati
            FROM parca
            ORDER BY id DESC
        """)
        rows = cursor.fetchall()
        return jsonify([
            {
                "id": r[0],
                "ad": r[1],
                "stok": r[2],
                "alis_fiyati": float(r[3] or 0),
                "satis_fiyati": float(r[4] or 0),
            } for r in rows
        ]), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500


# ▶ Tek parça detayı
@parca_bp.route("/parca/<int:parca_id>", methods=["GET"])
def parca_detay(parca_id):
    try:
        cursor.execute("""
            SELECT id, ad, stok, alis_fiyati, satis_fiyati
            FROM parca WHERE id = %s
        """, (parca_id,))
        r = cursor.fetchone()
        if not r:
            return jsonify({"durum": "hata", "mesaj": "Parça bulunamadı"}), 404
        return jsonify({
            "id": r[0], "ad": r[1], "stok": r[2],
            "alis_fiyati": float(r[3] or 0),
            "satis_fiyati": float(r[4] or 0)
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500


# ▶ Parça güncelle
@parca_bp.route("/parca/guncelle/<int:parca_id>", methods=["POST"])
def parca_guncelle(parca_id):
    try:
        ad            = _g("ad")
        stok          = _g("stok", 0, int)
        alis_fiyati   = _g("alis_fiyati", 0.0, float)
        satis_fiyati  = _g("satis_fiyati", 0.0, float)

        cursor.execute("""
            UPDATE parca SET
                ad = COALESCE(%s, ad),
                stok = GREATEST(%s, 0),
                alis_fiyati  = %s,
                satis_fiyati = %s
            WHERE id = %s
        """, (ad, stok, alis_fiyati, satis_fiyati, parca_id))
        conn.commit()
        return jsonify({"durum": "başarılı", "mesaj": "Parça güncellendi"}), 200
    except Exception as e:
        traceback.print_exc()
        conn.rollback()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500


# ▶ Parça tamamen sil  (stok geri eklenmez - servis parçaları JSON’da saklandığı için ilişki yok)
@parca_bp.route("/parca/sil/<int:parca_id>", methods=["DELETE"])
def parca_sil(parca_id):
    try:
        cursor.execute("DELETE FROM parca WHERE id = %s", (parca_id,))
        conn.commit()
        return jsonify({"durum": "başarılı", "mesaj": "Parça silindi"}), 200
    except Exception as e:
        traceback.print_exc()
        conn.rollback()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500


# ▶ Stok artır
@parca_bp.route("/parca/stok-arttir", methods=["POST"])
def parca_stok_arttir():
    try:
        parca_id = _g("id", None, int)
        miktar   = _g("miktar", 0, int)
        if not parca_id or miktar <= 0:
            return jsonify({"durum": "hata", "mesaj": "Geçersiz parametre"}), 400

        cursor.execute("UPDATE parca SET stok = stok + %s WHERE id = %s",
                       (miktar, parca_id))
        conn.commit()
        return jsonify({"durum": "başarılı", "mesaj": "Stok artırıldı"}), 200
    except Exception as e:
        traceback.print_exc()
        conn.rollback()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500


# ▶ Stok azalt  (stok asla negatif olmaz)
@parca_bp.route("/parca/stok-azalt", methods=["POST"])
def parca_stok_azalt():
    try:
        parca_id = _g("id", None, int)
        miktar   = _g("miktar", 0, int)
        if not parca_id or miktar <= 0:
            return jsonify({"durum": "hata", "mesaj": "Geçersiz parametre"}), 400

        cursor.execute("""
            UPDATE parca
            SET stok = GREATEST(stok - %s, 0)
            WHERE id = %s
        """, (miktar, parca_id))
        conn.commit()
        return jsonify({"durum": "başarılı", "mesaj": "Stok azaltıldı"}), 200
    except Exception as e:
        traceback.print_exc()
        conn.rollback()
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

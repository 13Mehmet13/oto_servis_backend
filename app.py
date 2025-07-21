from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# Route Blueprint'leri
from routes.parca_routes import parca_bp
from routes.musteri_routes import musteri_bp
from routes.arac_routes import arac_bp
from routes.servis_routes import servis_bp
from routes.servis_pdf_routes import servis_pdf_bp
from routes.rapor_routes import rapor_bp
from routes.giris_routes import giris_bp
from routes.marka_routes import marka_bp
from routes.cari_routes import cari_bp

# Uygulama başlat
app = Flask(__name__)
CORS(app)

# ✅ Gerekli ayarlar
app.secret_key = "gizli_kelime"  # Session için
app.config["JWT_SECRET_KEY"] = "gizli_kelime"  # JWT için

# JWT başlat
jwt = JWTManager(app)

# Blueprint kayıtları
app.register_blueprint(parca_bp)
app.register_blueprint(musteri_bp)
app.register_blueprint(arac_bp)
app.register_blueprint(servis_bp)
app.register_blueprint(servis_pdf_bp)
app.register_blueprint(rapor_bp)
app.register_blueprint(giris_bp)
app.register_blueprint(marka_bp)
app.register_blueprint(cari_bp)

# Ana rota
@app.route("/")
def home():
    return "🚀 Oto Servis API aktif!"

# Uygulamayı başlat
# Uygulamayı başlatma (systemd ya da gunicorn kullanıldığı için gerek yok)
# if __name__ == "__main__":
#     app.run(debug=True, host="0.0.0.0", port=5000)

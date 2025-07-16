from functools import wraps
from flask import session, jsonify

def rol_kontrol(gerekli_rol):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get("rol") != gerekli_rol:
                return jsonify({"durum": "hata", "mesaj": "Yetkiniz yok"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

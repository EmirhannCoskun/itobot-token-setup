import os
import secrets
import re
import time

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session
)

import requests

from token_manager import (
    save_token,
    get_token,
    delete_token
)


app = Flask(__name__)


# ========================================
# UYGULAMA GÜVENLİK AYARLARI
# ========================================

app.config["SECRET_KEY"] = (
    os.environ.get("FLASK_SECRET_KEY")
    or secrets.token_hex(32)
)

# Token gibi küçük JSON istekleri için fazlasıyla yeterli.
app.config["MAX_CONTENT_LENGTH"] = 4096


# ========================================
# SUNUCU AYARLARI
# ========================================

HOST = "127.0.0.1"
PORT = 5000


# ========================================
# CSRF AYARLARI
# ========================================

CSRF_HEADER_NAME = "X-CSRF-Token"


def get_csrf_token():
    """
    Mevcut session için CSRF tokenı döndürür.

    Session içerisinde token yoksa güvenli rastgele
    bir token oluşturur.
    """

    token = session.get("csrf_token")

    if not isinstance(token, str) or not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token

    return token


def validate_csrf_token():
    """
    İstek içerisindeki CSRF tokenı session'daki
    token ile karşılaştırır.

    Güvenli karşılaştırma için secrets.compare_digest()
    kullanılır.
    """

    session_token = session.get("csrf_token")

    request_token = request.headers.get(
        CSRF_HEADER_NAME
    )

    if not isinstance(session_token, str):
        return False

    if not isinstance(request_token, str):
        return False

    if not session_token or not request_token:
        return False

    return secrets.compare_digest(
        session_token,
        request_token
    )


def csrf_error_response():
    """
    CSRF doğrulaması başarısız olduğunda
    standart JSON cevabı döndürür.
    """

    return jsonify({
        "success": False,
        "message": "Geçersiz güvenlik doğrulaması."
    }), 403


# ========================================
# SECURITY HEADERS
# ========================================

@app.after_request
def add_security_headers(response):
    """
    Her HTTP cevabına temel güvenlik header'larını ekler.
    """

    # MIME type sniffing saldırılarını engeller.
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Sayfanın iframe içerisinde açılmasını engeller.
    response.headers["X-Frame-Options"] = "DENY"

    # Referrer bilgisinin başka sitelere gönderilmesini sınırlar.
    response.headers["Referrer-Policy"] = "no-referrer"

    # İçerik güvenlik politikası.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )

    return response


# ========================================
# RATE LIMIT AYARLARI
# ========================================

RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_REQUESTS = 5

# İstemci IP adreslerine ait istek zamanları.
rate_limit_store = {}


# ========================================
# RATE LIMIT KONTROLÜ
# ========================================

def is_rate_limited(client_ip: str) -> bool:
    """
    Bir istemcinin /save-token endpoint'i için
    rate limit sınırını aşıp aşmadığını kontrol eder.
    """

    now = time.monotonic()

    request_times = rate_limit_store.get(
        client_ip,
        []
    )

    # Pencere dışındaki eski istekleri temizle.
    request_times = [
        timestamp
        for timestamp in request_times
        if now - timestamp < RATE_LIMIT_WINDOW
    ]

    if len(request_times) >= RATE_LIMIT_MAX_REQUESTS:
        rate_limit_store[client_ip] = request_times
        return True

    # Yeni isteği kaydet.
    request_times.append(now)
    rate_limit_store[client_ip] = request_times

    return False


# ========================================
# TELEGRAM TOKEN FORMAT KONTROLÜ
# ========================================

TOKEN_PATTERN = re.compile(
    r"^\d{6,20}:[A-Za-z0-9_-]{20,}$"
)


def is_valid_token_format(token: str) -> bool:
    """
    Tokenın temel Telegram Bot Token formatına
    uyup uymadığını kontrol eder.

    Bu kontrol tokenın gerçekten geçerli olduğunu
    kanıtlamaz.
    """

    if not isinstance(token, str):
        return False

    token = token.strip()

    if not token:
        return False

    if len(token) > 256:
        return False

    return bool(
        TOKEN_PATTERN.fullmatch(token)
    )


# ========================================
# TELEGRAM TOKEN DOĞRULAMA
# ========================================

def validate_telegram_token(token: str):
    """
    Tokenı Telegram Bot API üzerinden doğrular.

    Başarılı:
        (True, bot_username)

    Başarısız:
        (False, None)
    """

    telegram_url = (
        f"https://api.telegram.org/bot{token}/getMe"
    )

    try:

        response = requests.get(
            telegram_url,
            timeout=(5, 10)
        )

    except requests.exceptions.Timeout:

        return False, None

    except requests.exceptions.RequestException:

        return False, None

    # Telegram HTTP seviyesinde hata döndürdüyse
    # JSON'u işlemeye gerek yok.
    if not response.ok:
        return False, None

    try:

        data = response.json()

    except ValueError:

        return False, None

    if not isinstance(data, dict):
        return False, None

    if data.get("ok") is not True:
        return False, None

    result = data.get("result")

    if not isinstance(result, dict):
        return False, None

    bot_username = result.get("username")

    if not isinstance(bot_username, str):
        bot_username = None

    return True, bot_username


# ========================================
# ANA SAYFA
# ========================================

@app.route("/", methods=["GET"])
def home():

    csrf_token = get_csrf_token()
    token = get_token()

    if token:

        return render_template(
            "success.html",
            csrf_token=csrf_token
        )

    return render_template(
        "setup.html",
        csrf_token=csrf_token
    )


# ========================================
# TOKEN KAYDET
# ========================================

@app.route("/save-token", methods=["POST"])
def save_token_route():

    # ------------------------------------
    # RATE LIMIT KONTROLÜ
    # ------------------------------------

    client_ip = (
        request.remote_addr
        or "unknown"
    )

    if is_rate_limited(client_ip):

        return jsonify({
            "success": False,
            "message": (
                "Çok fazla istek gönderildi. "
                "Lütfen biraz bekleyip tekrar deneyin."
            )
        }), 429


    # ------------------------------------
    # Content-Type kontrolü
    # ------------------------------------

    if not request.is_json:

        return jsonify({
            "success": False,
            "message": "Geçersiz istek formatı."
        }), 415


    # ------------------------------------
    # JSON kontrolü
    # ------------------------------------

    data = request.get_json(
        silent=True
    )

    if not isinstance(data, dict):

        return jsonify({
            "success": False,
            "message": "Geçersiz istek."
        }), 400


    # ------------------------------------
    # CSRF KONTROLÜ
    # ------------------------------------

    if not validate_csrf_token():

        return csrf_error_response()


    # ------------------------------------
    # Token kontrolü
    # ------------------------------------

    token = data.get("token")

    if not isinstance(token, str):

        return jsonify({
            "success": False,
            "message": "Geçersiz token."
        }), 400


    token = token.strip()


    if not token:

        return jsonify({
            "success": False,
            "message": "Token boş bırakılamaz."
        }), 400


    # ------------------------------------
    # Token format kontrolü
    # ------------------------------------

    if not is_valid_token_format(token):

        return jsonify({
            "success": False,
            "message": (
                "Geçersiz Telegram Bot Token formatı."
            )
        }), 400


    # ------------------------------------
    # Telegram API doğrulaması
    # ------------------------------------

    is_valid, bot_username = (
        validate_telegram_token(token)
    )


    if not is_valid:

        return jsonify({
            "success": False,
            "message": (
                "Telegram Bot Token doğrulanamadı. "
                "Tokenın doğru olduğundan emin olun."
            )
        }), 400


    # ------------------------------------
    # Tokenı kaydet
    # ------------------------------------

    try:

        save_token(token)

    except (
        OSError,
        TypeError,
        ValueError
    ):

        return jsonify({
            "success": False,
            "message": (
                "Token güvenli şekilde kaydedilemedi."
            )
        }), 500


    # ------------------------------------
    # Başarılı cevap
    # ------------------------------------

    message = (
        "Token başarıyla doğrulandı ve kaydedildi."
    )

    if bot_username:

        message += (
            f" Bot: @{bot_username}"
        )


    return jsonify({
        "success": True,
        "message": message
    }), 200


# ========================================
# BAŞARI SAYFASI
# ========================================

@app.route("/success", methods=["GET"])
def success():

    csrf_token = get_csrf_token()
    token = get_token()

    if not token:

        return render_template(
            "setup.html",
            csrf_token=csrf_token
        )

    return render_template(
        "success.html",
        csrf_token=csrf_token
    )


# ========================================
# TOKEN DEĞİŞTİRME EKRANI
# ========================================

@app.route("/change-token", methods=["GET"])
def change_token():

    csrf_token = get_csrf_token()

    return render_template(
        "setup.html",
        csrf_token=csrf_token
    )


# ========================================
# TOKEN SİL
# ========================================

@app.route("/delete-token", methods=["POST"])
def delete_token_route():
    """
    Kayıtlı Telegram bot tokenını siler.
    """

    # ------------------------------------
    # CSRF KONTROLÜ
    # ------------------------------------

    if not validate_csrf_token():

        return csrf_error_response()


    # ------------------------------------
    # TOKEN SİLME
    # ------------------------------------

    try:

        deleted = delete_token()

    except OSError:

        return jsonify({
            "success": False,
            "message": "Token silinemedi."
        }), 500


    if not deleted:

        return jsonify({
            "success": False,
            "message": (
                "Kayıtlı token bulunamadı."
            )
        }), 404


    return jsonify({
        "success": True,
        "message": "Token başarıyla silindi."
    }), 200


# ========================================
# UYGULAMAYI BAŞLAT
# ========================================

if __name__ == "__main__":

    app.run(
        host=HOST,
        port=PORT,
        debug=False
    )

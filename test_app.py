import pytest

import app
import token_manager


@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    Flask test client oluşturur.

    Testler gerçek data/config.json dosyasına
    dokunmaz. Her test geçici bir config kullanır.

    CSRF token test session'ına otomatik olarak
    oluşturulur ve normal test isteklerine header
    olarak otomatik eklenir.
    """

    test_data_dir = tmp_path / "data"
    test_token_file = test_data_dir / "config.json"

    monkeypatch.setattr(
        token_manager,
        "DATA_DIR",
        test_data_dir
    )

    monkeypatch.setattr(
        token_manager,
        "TOKEN_FILE",
        test_token_file
    )

    app.app.config.update({
        "TESTING": True
    })

    app.rate_limit_store.clear()

    with app.app.test_client() as client:

        # Ana sayfayı açarak session içerisinde
        # CSRF token oluştur.
        client.get("/")

        # Session içerisindeki CSRF tokenı al.
        with client.session_transaction() as session:

            csrf_token = session.get(
                "csrf_token"
            )

        # Normal test isteklerine CSRF tokenı
        # otomatik olarak ekle.
        client.environ_base[
            "HTTP_X_CSRF_TOKEN"
        ] = csrf_token

        yield client


# ========================================
# ANA SAYFA
# ========================================

def test_home_without_token(client):

    response = client.get("/")

    assert response.status_code == 200
    assert b"setup" in response.data.lower()


def test_home_with_token(client):

    token_manager.save_token(
        "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    response = client.get("/")

    assert response.status_code == 200
    assert b"success.js" in response.data


# ========================================
# SUCCESS SAYFASI
# ========================================

def test_success_without_token(client):

    response = client.get("/success")

    assert response.status_code == 200
    assert b"setup" in response.data.lower()


def test_success_with_token(client):

    token_manager.save_token(
        "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    response = client.get("/success")

    assert response.status_code == 200
    assert b"success.js" in response.data


# ========================================
# SAVE TOKEN - TEMEL VALIDASYON
# ========================================

def test_save_token_without_json(client):

    response = client.post(
        "/save-token"
    )

    assert response.status_code == 415


def test_save_token_with_empty_json(client):

    with client.session_transaction() as session:
        csrf_token = session["csrf_token"]

    response = client.post(
        "/save-token",
        json={},
        headers={
            "X-CSRF-Token": csrf_token
        }
    )

    assert response.status_code == 400


def test_save_token_with_empty_token(client):

    with client.session_transaction() as session:
        csrf_token = session["csrf_token"]

    response = client.post(
        "/save-token",
        json={
            "token": ""
        },
        headers={
            "X-CSRF-Token": csrf_token
        }
    )

    assert response.status_code == 400


# ========================================
# TOKEN DEĞİŞTİRME EKRANI
# ========================================

def test_change_token_page(client):

    response = client.get("/change-token")

    assert response.status_code == 200
    assert b"setup" in response.data.lower()


def test_change_token_keeps_existing_token(client):

    old_token = (
        "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    token_manager.save_token(old_token)

    response = client.get("/change-token")

    assert response.status_code == 200

    # Yeni token henüz kaydedilmediği için
    # eski token korunmalı.
    assert token_manager.get_token() == old_token


# ========================================
# TELEGRAM API MOCK TESTLERİ
# ========================================

def test_save_token_with_valid_telegram_response(
    client,
    monkeypatch
):
    """
    Telegram API geçerli cevap verirse token kaydedilmeli.
    """

    def mock_get(*args, **kwargs):

        class MockResponse:

            ok = True

            def json(self):
                return {
                    "ok": True,
                    "result": {
                        "username": "test_bot"
                    }
                }

        return MockResponse()

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    response = client.post(
        "/save-token",
        json={
            "token": token
        }
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True
    assert "test_bot" in data["message"]

    assert token_manager.get_token() == token


def test_save_token_with_invalid_telegram_response(
    client,
    monkeypatch
):
    """
    Telegram API tokenı geçersiz olarak bildirirse
    token kaydedilmemeli.
    """

    def mock_get(*args, **kwargs):

        class MockResponse:

            ok = True

            def json(self):
                return {
                    "ok": False
                }

        return MockResponse()

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    response = client.post(
        "/save-token",
        json={
            "token": token
        }
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["success"] is False

    assert token_manager.get_token() is None


def test_save_token_telegram_http_error(
    client,
    monkeypatch
):
    """
    Telegram HTTP seviyesinde hata döndürürse
    token kaydedilmemeli.
    """

    def mock_get(*args, **kwargs):

        class MockResponse:

            ok = False

            def json(self):
                return {
                    "ok": False
                }

        return MockResponse()

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    response = client.post(
        "/save-token",
        json={
            "token": token
        }
    )

    assert response.status_code == 400

    assert token_manager.get_token() is None


def test_save_token_telegram_timeout(
    client,
    monkeypatch
):
    """
    Telegram API timeout verirse uygulama kontrollü
    şekilde hata döndürmeli.
    """

    def mock_get(*args, **kwargs):

        raise app.requests.exceptions.Timeout()

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    response = client.post(
        "/save-token",
        json={
            "token": token
        }
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["success"] is False

    assert token_manager.get_token() is None


def test_save_token_telegram_connection_error(
    client,
    monkeypatch
):
    """
    Telegram API bağlantı hatası oluşursa token
    kaydedilmemeli.
    """

    def mock_get(*args, **kwargs):

        raise app.requests.exceptions.ConnectionError()

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    response = client.post(
        "/save-token",
        json={
            "token": token
        }
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["success"] is False

    assert token_manager.get_token() is None


def test_save_token_telegram_invalid_json(
    client,
    monkeypatch
):
    """
    Telegram geçersiz/bozuk JSON döndürürse token
    kaydedilmemeli.
    """

    def mock_get(*args, **kwargs):

        class MockResponse:

            ok = True

            def json(self):
                raise ValueError(
                    "Invalid JSON"
                )

        return MockResponse()

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    response = client.post(
        "/save-token",
        json={
            "token": token
        }
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["success"] is False

    assert token_manager.get_token() is None


# ========================================
# SECURITY HEADERS TESTLERİ
# ========================================

def test_security_headers_on_home(client):
    """
    Ana sayfanın temel security header'larını
    içerdiğini kontrol eder.
    """

    response = client.get("/")

    assert response.status_code == 200

    assert (
        response.headers["X-Content-Type-Options"]
        == "nosniff"
    )

    assert (
        response.headers["X-Frame-Options"]
        == "DENY"
    )

    assert (
        response.headers["Referrer-Policy"]
        == "no-referrer"
    )

    assert (
        "default-src 'self'"
        in response.headers["Content-Security-Policy"]
    )

    assert (
        "object-src 'none'"
        in response.headers["Content-Security-Policy"]
    )


def test_security_headers_on_success(client):
    """
    Başarı sayfasının da security header'larını
    içerdiğini kontrol eder.
    """

    token_manager.save_token(
        "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    response = client.get("/success")

    assert response.status_code == 200

    assert (
        response.headers["X-Content-Type-Options"]
        == "nosniff"
    )

    assert (
        response.headers["X-Frame-Options"]
        == "DENY"
    )

    assert (
        response.headers["Referrer-Policy"]
        == "no-referrer"
    )

    assert (
        "default-src 'self'"
        in response.headers["Content-Security-Policy"]
    )


def test_security_headers_on_api_response(client):
    """
    API cevaplarının da security header'larını
    içerdiğini kontrol eder.
    """

    with client.session_transaction() as session:
        csrf_token = session["csrf_token"]

    response = client.post(
        "/save-token",
        json={},
        headers={
            "X-CSRF-Token": csrf_token
        }
    )

    assert response.status_code == 400

    assert (
        response.headers["X-Content-Type-Options"]
        == "nosniff"
    )

    assert (
        response.headers["X-Frame-Options"]
        == "DENY"
    )

    assert (
        response.headers["Referrer-Policy"]
        == "no-referrer"
    )

    assert (
        "default-src 'self'"
        in response.headers["Content-Security-Policy"]
    )


# ========================================
# RATE LIMIT TESTLERİ
# ========================================

def test_save_token_rate_limit(
    client,
    monkeypatch
):
    """
    Aynı istemci kısa süre içerisinde izin verilen
    istek sayısını aşarsa 429 döndürülmeli.
    """

    def mock_get(*args, **kwargs):

        class MockResponse:

            ok = True

            def json(self):
                return {
                    "ok": True,
                    "result": {
                        "username": "test_bot"
                    }
                }

        return MockResponse()

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    for _ in range(
        app.RATE_LIMIT_MAX_REQUESTS
    ):

        response = client.post(
            "/save-token",
            json={
                "token": token
            }
        )

        assert response.status_code == 200

    response = client.post(
        "/save-token",
        json={
            "token": token
        }
    )

    assert response.status_code == 429

    data = response.get_json()

    assert data["success"] is False

    assert (
        "Çok fazla istek"
        in data["message"]
    )


def test_rate_limit_blocks_only_limited_ip(
    client,
    monkeypatch
):
    """
    Rate limit bir istemciyi etkilerken başka bir
    IP adresinin isteğini engellememeli.
    """

    def mock_get(*args, **kwargs):

        class MockResponse:

            ok = True

            def json(self):
                return {
                    "ok": True,
                    "result": {
                        "username": "test_bot"
                    }
                }

        return MockResponse()

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    for _ in range(
        app.RATE_LIMIT_MAX_REQUESTS
    ):

        response = client.post(
            "/save-token",
            json={
                "token": token
            },
            environ_base={
                "REMOTE_ADDR": "127.0.0.1"
            }
        )

        assert response.status_code == 200

    blocked_response = client.post(
        "/save-token",
        json={
            "token": token
        },
        environ_base={
            "REMOTE_ADDR": "127.0.0.1"
        }
    )

    assert blocked_response.status_code == 429

    other_client_response = client.post(
        "/save-token",
        json={
            "token": token
        },
        environ_base={
            "REMOTE_ADDR": "192.168.1.50"
        }
    )

    assert other_client_response.status_code == 200


# ========================================
# HATA YÖNETİMİ VE TOKEN KORUMA TESTLERİ
# ========================================

def test_invalid_new_token_keeps_old_token(
    client,
    monkeypatch
):
    """
    Yeni token geçersizse mevcut geçerli token
    kesinlikle değiştirilmemeli.
    """

    old_token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    new_token = (
        "987654321:"
        "ZYXWVUTSRQPONMLKJIHGFEDCBAabc"
    )

    token_manager.save_token(old_token)

    def mock_get(*args, **kwargs):

        class MockResponse:

            ok = True

            def json(self):
                return {
                    "ok": False
                }

        return MockResponse()

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    response = client.post(
        "/save-token",
        json={
            "token": new_token
        }
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["success"] is False

    assert token_manager.get_token() == old_token


def test_save_token_when_file_write_fails(
    client,
    monkeypatch
):
    """
    Token dosyasına yazma işlemi başarısız olursa
    uygulama kontrollü şekilde 500 döndürmeli.
    """

    def mock_save_token(token):
        raise OSError("Disk yazma hatası")

    monkeypatch.setattr(
        app,
        "save_token",
        mock_save_token
    )

    def mock_get(*args, **kwargs):

        class MockResponse:

            ok = True

            def json(self):
                return {
                    "ok": True,
                    "result": {
                        "username": "test_bot"
                    }
                }

        return MockResponse()

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    response = client.post(
        "/save-token",
        json={
            "token": token
        }
    )

    assert response.status_code == 500

    data = response.get_json()

    assert data["success"] is False

    assert (
        "kaydedilemedi"
        in data["message"]
    )


# ========================================
# REQUEST BOYUTU TESTİ
# ========================================

def test_save_token_request_too_large(client):
    """
    Çok büyük bir request gönderildiğinde Flask
    isteği reddetmeli.
    """

    huge_payload = {
        "token": "A" * 5000
    }

    response = client.post(
        "/save-token",
        json=huge_payload
    )

    assert response.status_code == 413


# ========================================
# TOKEN FORMAT + TELEGRAM API TESTİ
# ========================================

def test_invalid_token_format_does_not_call_telegram(
    client,
    monkeypatch
):
    """
    Formatı geçersiz bir token için Telegram API'ye
    gereksiz istek gönderilmemeli.
    """

    telegram_called = False

    def mock_get(*args, **kwargs):
        nonlocal telegram_called

        telegram_called = True

        raise AssertionError(
            "Geçersiz token için Telegram API çağrılmamalı."
        )

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    response = client.post(
        "/save-token",
        json={
            "token": "bu-gecersiz-bir-token"
        }
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["success"] is False

    assert (
        "formatı"
        in data["message"]
    )

    assert telegram_called is False


# ========================================
# RATE LIMIT + TELEGRAM API TESTİ
# ========================================

def test_rate_limit_blocks_telegram_request(
    client,
    monkeypatch
):
    """
    Rate limit aşıldığında Telegram API'ye
    yeni istek gönderilmemeli.
    """

    telegram_call_count = 0

    def mock_get(*args, **kwargs):
        nonlocal telegram_call_count

        telegram_call_count += 1

        class MockResponse:

            ok = True

            def json(self):
                return {
                    "ok": True,
                    "result": {
                        "username": "test_bot"
                    }
                }

        return MockResponse()

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    for _ in range(
        app.RATE_LIMIT_MAX_REQUESTS
    ):

        response = client.post(
            "/save-token",
            json={
                "token": token
            }
        )

        assert response.status_code == 200

    assert (
        telegram_call_count
        == app.RATE_LIMIT_MAX_REQUESTS
    )

    response = client.post(
        "/save-token",
        json={
            "token": token
        }
    )

    assert response.status_code == 429

    assert (
        telegram_call_count
        == app.RATE_LIMIT_MAX_REQUESTS
    )


# ========================================
# BOZUK CONFIG TESTLERİ
# ========================================

def test_home_with_corrupted_config(client):
    """
    config.json bozuksa uygulama çökmemeli ve
    kullanıcı kurulum ekranına yönlendirilmelidir.
    """

    client.get("/")

    token_manager.TOKEN_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    token_manager.TOKEN_FILE.write_text(
        "{ bozuk json !!!",
        encoding="utf-8"
    )

    response = client.get("/")

    assert response.status_code == 200

    assert b"setup" in response.data.lower()


def test_success_with_corrupted_config(client):
    """
    config.json bozuksa /success endpoint'i de
    güvenli şekilde setup ekranını göstermeli.
    """

    token_manager.TOKEN_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    token_manager.TOKEN_FILE.write_text(
        "{ bozuk json !!!",
        encoding="utf-8"
    )

    response = client.get("/success")

    assert response.status_code == 200

    assert b"setup" in response.data.lower()


# ========================================
# TOKEN GİZLİLİĞİ TESTLERİ
# ========================================

def test_token_is_not_exposed_in_home_response(client):
    """
    Kayıtlı token ana sayfanın HTML çıktısında
    bulunmamalı.
    """

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    token_manager.save_token(token)

    response = client.get("/")

    assert response.status_code == 200

    assert token.encode() not in response.data


def test_token_is_not_exposed_in_success_response(client):
    """
    Kayıtlı token başarı sayfasının HTML çıktısında
    bulunmamalı.
    """

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    token_manager.save_token(token)

    response = client.get("/success")

    assert response.status_code == 200

    assert token.encode() not in response.data


def test_token_is_not_returned_by_save_token_response(
    client,
    monkeypatch
):
    """
    Token başarıyla kaydedildiğinde API cevabında
    tokenın kendisi döndürülmemeli.
    """

    def mock_get(*args, **kwargs):

        class MockResponse:

            ok = True

            def json(self):
                return {
                    "ok": True,
                    "result": {
                        "username": "test_bot"
                    }
                }

        return MockResponse()

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    response = client.post(
        "/save-token",
        json={
            "token": token
        }
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True

    assert token not in response.get_data(
        as_text=True
    )


# ========================================
# TOKEN DEĞİŞTİRME GÜVENLİK TESTLERİ
# ========================================

def test_valid_new_token_replaces_old_token(
    client,
    monkeypatch
):
    """
    Geçerli yeni token doğrulandıktan sonra
    eski token yeni token ile değiştirilmelidir.
    """

    old_token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    new_token = (
        "987654321:"
        "ZYXWVUTSRQPONMLKJIHGFEDCBAabc"
    )

    token_manager.save_token(old_token)

    def mock_get(*args, **kwargs):

        class MockResponse:

            ok = True

            def json(self):
                return {
                    "ok": True,
                    "result": {
                        "username": "new_test_bot"
                    }
                }

        return MockResponse()

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    response = client.post(
        "/save-token",
        json={
            "token": new_token
        }
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True
    assert "new_test_bot" in data["message"]

    assert token_manager.get_token() == new_token

    assert token_manager.get_token() != old_token


# ========================================
# TOKEN SİLME GÜVENLİK TESTLERİ
# ========================================

def test_delete_token_removes_existing_token(client):
    """
    Kayıtlı token silme endpoint'i başarılı şekilde
    tokenı kaldırmalı.
    """

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    token_manager.save_token(token)

    assert token_manager.get_token() == token

    response = client.post(
        "/delete-token"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True

    assert (
        "başarıyla silindi"
        in data["message"].lower()
    )

    assert token_manager.get_token() is None


def test_delete_token_without_existing_token(client):
    """
    Kayıtlı token yoksa silme endpoint'i 404
    döndürmeli.
    """

    assert token_manager.get_token() is None

    response = client.post(
        "/delete-token"
    )

    assert response.status_code == 404

    data = response.get_json()

    assert data["success"] is False


def test_delete_token_then_home_shows_setup(client):
    """
    Token silindikten sonra ana sayfa tekrar
    kurulum ekranını göstermeli.
    """

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    token_manager.save_token(token)

    delete_response = client.post(
        "/delete-token"
    )

    assert delete_response.status_code == 200

    response = client.get("/")

    assert response.status_code == 200

    assert b"setup" in response.data.lower()

    assert token_manager.get_token() is None


# ========================================
# TOKEN SİLME HATA TESTİ
# ========================================

def test_delete_token_when_file_delete_fails(
    client,
    monkeypatch
):
    """
    Token dosyası silinemediğinde endpoint kontrollü
    şekilde 500 döndürmeli.
    """

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    token_manager.save_token(token)

    def mock_delete_token():
        raise OSError("Dosya silme hatası")

    monkeypatch.setattr(
        app,
        "delete_token",
        mock_delete_token
    )

    response = client.post(
        "/delete-token"
    )

    assert response.status_code == 500

    data = response.get_json()

    assert data["success"] is False

    assert (
        "silinemedi"
        in data["message"].lower()
    )


# ========================================
# HTTP METHOD GÜVENLİK TESTLERİ
# ========================================

def test_save_token_rejects_get_request(client):
    """
    /save-token yalnızca POST kabul etmeli.
    """

    response = client.get("/save-token")

    assert response.status_code == 405


def test_delete_token_rejects_get_request(client):
    """
    /delete-token yalnızca POST kabul etmeli.
    """

    response = client.get("/delete-token")

    assert response.status_code == 405


def test_change_token_rejects_post_request(client):
    """
    /change-token yalnızca GET kabul etmeli.
    """

    response = client.post("/change-token")

    assert response.status_code == 405


# ========================================
# TOKEN VERİ TİPİ GÜVENLİK TESTLERİ
# ========================================

@pytest.mark.parametrize(
    "invalid_token",
    [
        None,
        123456789,
        [],
        {},
        True,
        False
    ]
)
def test_save_token_rejects_invalid_token_types(
    client,
    monkeypatch,
    invalid_token
):
    """
    Token alanı string dışında bir veri tipinde
    gönderilirse istek reddedilmeli.
    """

    telegram_called = False

    def mock_get(*args, **kwargs):
        nonlocal telegram_called

        telegram_called = True

        raise AssertionError(
            "Geçersiz token tipi için Telegram API çağrılmamalı."
        )

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    response = client.post(
        "/save-token",
        json={
            "token": invalid_token
        }
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["success"] is False

    assert telegram_called is False

    assert token_manager.get_token() is None


# ========================================
# İSTEK BOYUTU GÜVENLİK TESTİ
# ========================================

def test_save_token_rejects_oversized_request(client):
    """
    /save-token endpoint'i izin verilen maksimum
    request boyutunu aşan istekleri reddetmeli.
    """

    oversized_token = "A" * 10000

    response = client.post(
        "/save-token",
        json={
            "token": oversized_token
        }
    )

    assert response.status_code == 413

    assert token_manager.get_token() is None


# ========================================
# TOKEN SIZINTISI GÜVENLİK TESTLERİ
# ========================================

def test_token_not_exposed_on_home(client):
    """
    Kayıtlı token ana sayfanın HTML çıktısında
    görünmemeli.
    """

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    token_manager.save_token(token)

    response = client.get("/")

    assert response.status_code == 200
    assert token.encode() not in response.data


def test_token_not_exposed_on_success(client):
    """
    Kayıtlı token başarı sayfasının HTML çıktısında
    görünmemeli.
    """

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    token_manager.save_token(token)

    response = client.get("/success")

    assert response.status_code == 200
    assert token.encode() not in response.data


def test_token_not_exposed_on_change_token(client):
    """
    Token değiştirme ekranına gidildiğinde mevcut token
    HTML çıktısına gönderilmemeli.
    """

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    token_manager.save_token(token)

    response = client.get("/change-token")

    assert response.status_code == 200
    assert token.encode() not in response.data


# ========================================
# HATA CEVAPLARINDA TOKEN SIZINTISI TESTLERİ
# ========================================

def test_invalid_token_error_does_not_expose_token(
    client
):
    """
    Geçersiz token gönderildiğinde hata cevabı
    tokenın kendisini içermemeli.
    """

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    response = client.post(
        "/save-token",
        json={
            "token": token
        }
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["success"] is False

    assert token not in data["message"]


def test_missing_token_error_does_not_expose_data(
    client
):
    """
    Token alanı gönderilmediğinde hata cevabı
    hassas veri içermemeli.
    """

    with client.session_transaction() as session:
        csrf_token = session["csrf_token"]

    response = client.post(
        "/save-token",
        json={},
        headers={
            "X-CSRF-Token": csrf_token
        }
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["success"] is False

    assert (
        "token" not in data["message"].lower()
        or data["message"] == "Geçersiz token."
    )


# ========================================
# TELEGRAM API İSTEK GÜVENLİĞİ TESTLERİ
# ========================================

def test_telegram_api_request_uses_https_and_timeout(
    client,
    monkeypatch
):
    """
    Telegram API isteğinin HTTPS kullandığını ve
    bağlantı/read timeout değerlerinin ayarlandığını
    kontrol eder.
    """

    captured = {}

    def mock_get(url, **kwargs):

        captured["url"] = url
        captured["kwargs"] = kwargs

        class MockResponse:

            ok = True

            def json(self):
                return {
                    "ok": True,
                    "result": {
                        "username": "test_bot"
                    }
                }

        return MockResponse()

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    response = client.post(
        "/save-token",
        json={
            "token": token
        }
    )

    assert response.status_code == 200

    assert captured["url"].startswith(
        "https://api.telegram.org/"
    )

    assert captured["url"] == (
        "https://api.telegram.org/"
        f"bot{token}/getMe"
    )

    assert captured["kwargs"]["timeout"] == (5, 10)


# ========================================
# TOKEN DEĞİŞTİRME AKIŞI GÜVENLİK TESTLERİ
# ========================================

def test_change_token_does_not_delete_existing_token(
    client
):
    """
    Token değiştirme ekranına girildiğinde mevcut
    token silinmemeli.
    """

    old_token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    token_manager.save_token(old_token)

    response = client.get("/change-token")

    assert response.status_code == 200

    assert token_manager.get_token() == old_token


def test_failed_new_token_keeps_old_token(
    client,
    monkeypatch
):
    """
    Yeni token doğrulaması başarısız olursa mevcut
    token korunmalı.
    """

    old_token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    new_token = (
        "987654321:"
        "ZYXWVUTSRQPONMLKJIHGFEDCBAabc"
    )

    token_manager.save_token(old_token)

    def mock_get(*args, **kwargs):

        class MockResponse:

            ok = True

            def json(self):
                return {
                    "ok": False
                }

        return MockResponse()

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    response = client.post(
        "/save-token",
        json={
            "token": new_token
        }
    )

    assert response.status_code == 400

    assert token_manager.get_token() == old_token


def test_successful_new_token_replaces_old_token(
    client,
    monkeypatch
):
    """
    Yeni token Telegram tarafından doğrulanırsa
    eski token yeni token ile değiştirilmelidir.
    """

    old_token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    new_token = (
        "987654321:"
        "ZYXWVUTSRQPONMLKJIHGFEDCBAabc"
    )

    token_manager.save_token(old_token)

    def mock_get(*args, **kwargs):

        class MockResponse:

            ok = True

            def json(self):
                return {
                    "ok": True,
                    "result": {
                        "username": "new_test_bot"
                    }
                }

        return MockResponse()

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    response = client.post(
        "/save-token",
        json={
            "token": new_token
        }
    )

    assert response.status_code == 200

    assert token_manager.get_token() == new_token

    assert token_manager.get_token() != old_token


# ========================================
# HTTP METHOD GÜVENLİK TESTLERİ
# ========================================

@pytest.mark.parametrize(
    "method",
    [
        "get",
        "put",
        "patch",
        "delete"
    ]
)
def test_save_token_rejects_unsupported_methods(
    client,
    method
):
    """
    /save-token endpoint'i yalnızca POST kabul etmeli.
    Diğer HTTP methodları 405 döndürmeli.
    """

    response = getattr(client, method)(
        "/save-token"
    )

    assert response.status_code == 405


@pytest.mark.parametrize(
    "method",
    [
        "get",
        "put",
        "patch",
        "delete"
    ]
)
def test_delete_token_rejects_unsupported_methods(
    client,
    method
):
    """
    /delete-token endpoint'i yalnızca POST kabul etmeli.
    """

    response = getattr(client, method)(
        "/delete-token"
    )

    assert response.status_code == 405


# ========================================
# HATA YÖNETİMİ VE BİLGİ SIZINTISI TESTLERİ
# ========================================

def test_save_token_storage_error_does_not_expose_token(
    client,
    monkeypatch
):
    """
    Token kaydedilirken beklenmeyen bir dosya hatası
    oluşursa kullanıcıya hassas bilgi döndürülmemeli.
    """

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    def mock_get(*args, **kwargs):

        class MockResponse:

            ok = True

            def json(self):
                return {
                    "ok": True,
                    "result": {
                        "username": "test_bot"
                    }
                }

        return MockResponse()

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    def mock_save_token(_token):
        raise OSError(
            "SECRET_INTERNAL_PATH"
        )

    monkeypatch.setattr(
        app,
        "save_token",
        mock_save_token
    )

    response = client.post(
        "/save-token",
        json={
            "token": token
        }
    )

    assert response.status_code == 500

    data = response.get_json()

    assert data["success"] is False

    assert token not in response.get_data(
        as_text=True
    )

    assert "SECRET_INTERNAL_PATH" not in response.get_data(
        as_text=True
    )

    assert "Traceback" not in response.get_data(
        as_text=True
    )


# ========================================
# TOKEN DEĞİŞTİRME GÜVENLİK TESTLERİ
# ========================================

def test_invalid_new_token_keeps_old_token(
    client,
    monkeypatch
):
    """
    Token değiştirme sırasında yeni token geçersizse
    mevcut eski token korunmalı.
    """

    old_token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    new_token = (
        "987654321:"
        "ZYXWVUTSRQPONMLKJIHGFEDCBAabc"
    )

    token_manager.save_token(old_token)

    def mock_get(*args, **kwargs):

        class MockResponse:

            ok = True

            def json(self):
                return {
                    "ok": False
                }

        return MockResponse()

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    response = client.post(
        "/save-token",
        json={
            "token": new_token
        }
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["success"] is False

    assert token_manager.get_token() == old_token

    assert token_manager.get_token() != new_token


# ========================================
# CSRF TESTLERİ
# ========================================

def test_save_token_rejects_missing_csrf(
    client
):
    """
    /save-token CSRF token gönderilmeden çağrılırsa
    403 döndürmeli.
    """

    with app.app.test_client() as csrf_free_client:

        csrf_free_client.get("/")

        response = csrf_free_client.post(
            "/save-token",
            json={}
        )

    assert response.status_code == 403

    data = response.get_json()

    assert data["success"] is False

    assert (
        "güvenlik"
        in data["message"].lower()
    )


def test_save_token_rejects_invalid_csrf(
    client
):
    """
    /save-token geçersiz CSRF token ile
    çağrılırsa 403 döndürmeli.
    """

    response = client.post(
        "/save-token",
        json={
            "token": (
                "123456789:"
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
            )
        },
        headers={
            "X-CSRF-Token": "invalid-csrf-token"
        }
    )

    assert response.status_code == 403

    data = response.get_json()

    assert data["success"] is False


def test_save_token_accepts_valid_csrf(
    client,
    monkeypatch
):
    """
    Geçerli CSRF token gönderildiğinde istek
    CSRF kontrolünü geçebilmeli.
    """

    def mock_get(*args, **kwargs):

        class MockResponse:

            ok = True

            def json(self):

                return {
                    "ok": True,
                    "result": {
                        "username": "test_bot"
                    }
                }

        return MockResponse()

    monkeypatch.setattr(
        app.requests,
        "get",
        mock_get
    )

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    response = client.post(
        "/save-token",
        json={
            "token": token
        }
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True


def test_delete_token_rejects_missing_csrf(
    client
):
    """
    /delete-token CSRF token olmadan çağrılırsa
    403 döndürmeli.
    """

    with app.app.test_client() as csrf_free_client:

        csrf_free_client.get("/")

        response = csrf_free_client.post(
            "/delete-token"
        )

    assert response.status_code == 403

    data = response.get_json()

    assert data["success"] is False

    assert (
        "güvenlik"
        in data["message"].lower()
    )


def test_delete_token_rejects_invalid_csrf(
    client
):
    """
    /delete-token geçersiz CSRF token ile
    çağrılırsa 403 döndürmeli.
    """

    response = client.post(
        "/delete-token",
        headers={
            "X-CSRF-Token": "invalid-csrf-token"
        }
    )

    assert response.status_code == 403

    data = response.get_json()

    assert data["success"] is False


def test_delete_token_accepts_valid_csrf(
    client
):
    """
    Geçerli CSRF token gönderildiğinde
    /delete-token endpoint'i çalışabilmeli.
    """

    token = (
        "123456789:"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabc"
    )

    token_manager.save_token(token)

    response = client.post(
        "/delete-token"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True

    assert token_manager.get_token() is None


def test_csrf_token_is_created_for_session(
    client
):
    """
    Sayfa açıldığında session içerisinde CSRF
    token oluşturulmalı.
    """

    with client.session_transaction() as session:

        csrf_token = session.get(
            "csrf_token"
        )

    assert isinstance(
        csrf_token,
        str
    )

    assert len(csrf_token) >= 32


def test_csrf_token_is_stable_for_same_session(
    client
):
    """
    Aynı session içerisinde CSRF tokenı
    değişmemeli.
    """

    with client.session_transaction() as session:

        first_token = session.get(
            "csrf_token"
        )

    client.get("/")

    with client.session_transaction() as session:

        second_token = session.get(
            "csrf_token"
        )

    assert first_token == second_token


def test_csrf_token_changes_for_new_session(
    client
):
    """
    Yeni bir session oluşturulduğunda yeni
    CSRF tokenı oluşturulmalı.
    """

    with client.session_transaction() as session:

        first_token = session.get(
            "csrf_token"
        )

    with app.app.test_client() as new_client:

        new_client.get("/")

        with new_client.session_transaction() as session:

            second_token = session.get(
                "csrf_token"
            )

    assert first_token != second_token
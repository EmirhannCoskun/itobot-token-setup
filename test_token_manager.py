import json

import pytest

import token_manager


@pytest.fixture
def isolated_token_file(tmp_path, monkeypatch):
    """
    Her test için tamamen ayrı bir geçici data klasörü oluşturur.

    Gerçek:
        data/config.json

    yerine test sırasında:
        geçici_klasör/config.json

    kullanılır.
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

    return test_token_file


# ========================================
# SAVE / GET
# ========================================

def test_save_and_get_token(isolated_token_file):

    test_token = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabc"

    token_manager.save_token(test_token)

    assert isolated_token_file.exists()

    saved_token = token_manager.get_token()

    assert saved_token == test_token


# ========================================
# GET - DOSYA YOK
# ========================================

def test_get_token_when_file_does_not_exist(
    isolated_token_file
):

    assert not isolated_token_file.exists()

    assert token_manager.get_token() is None


# ========================================
# GET - BOZUK JSON
# ========================================

def test_get_token_with_invalid_json(
    isolated_token_file
):

    isolated_token_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    isolated_token_file.write_text(
        "{invalid json",
        encoding="utf-8"
    )

    assert token_manager.get_token() is None


# ========================================
# GET - JSON OBJECT DEĞİL
# ========================================

def test_get_token_with_non_dict_json(
    isolated_token_file
):

    isolated_token_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    isolated_token_file.write_text(
        json.dumps(["not", "a", "dictionary"]),
        encoding="utf-8"
    )

    assert token_manager.get_token() is None


# ========================================
# GET - TOKEN ALANI YOK
# ========================================

def test_get_token_with_missing_token(
    isolated_token_file
):

    isolated_token_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    isolated_token_file.write_text(
        json.dumps({
            "other_key": "value"
        }),
        encoding="utf-8"
    )

    assert token_manager.get_token() is None


# ========================================
# GET - TOKEN STRING DEĞİL
# ========================================

def test_get_token_with_invalid_token_type(
    isolated_token_file
):

    isolated_token_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    isolated_token_file.write_text(
        json.dumps({
            "telegram_bot_token": 123456
        }),
        encoding="utf-8"
    )

    assert token_manager.get_token() is None


# ========================================
# GET - TOKEN BOŞ
# ========================================

def test_get_token_with_empty_token(
    isolated_token_file
):

    isolated_token_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    isolated_token_file.write_text(
        json.dumps({
            "telegram_bot_token": "   "
        }),
        encoding="utf-8"
    )

    assert token_manager.get_token() is None


# ========================================
# SAVE - BOŞ TOKEN
# ========================================

def test_save_token_rejects_empty_string(
    isolated_token_file
):

    with pytest.raises(ValueError):

        token_manager.save_token("")


# ========================================
# SAVE - STRING DEĞİL
# ========================================

def test_save_token_rejects_non_string(
    isolated_token_file
):

    with pytest.raises(TypeError):

        token_manager.save_token(123456)


# ========================================
# DELETE
# ========================================

def test_delete_token(isolated_token_file):

    test_token = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabc"

    token_manager.save_token(test_token)

    assert isolated_token_file.exists()

    result = token_manager.delete_token()

    assert result is True

    assert not isolated_token_file.exists()


# ========================================
# DELETE - DOSYA YOK
# ========================================

def test_delete_token_when_file_does_not_exist(
    isolated_token_file
):

    assert not isolated_token_file.exists()

    result = token_manager.delete_token()

    assert result is False
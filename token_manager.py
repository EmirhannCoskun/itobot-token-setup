from pathlib import Path
import json
import os
import tempfile
from typing import Optional


# ========================================
# DOSYA YOLLARI
# ========================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
TOKEN_FILE = DATA_DIR / "config.json"


# ========================================
# SABİTLER
# ========================================

TOKEN_KEY = "telegram_bot_token"

# Config dosyasının kabul edebileceğimiz
# maksimum boyutu.
MAX_CONFIG_SIZE = 4096


# ========================================
# YARDIMCI FONKSİYONLAR
# ========================================

def _ensure_data_dir() -> None:
    """
    data klasörünün mevcut olduğundan emin olur.
    """
    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


def _is_valid_token_value(token: object) -> bool:
    """
    Token değerinin temel veri tipi kontrolünü yapar.

    Telegram tokenının gerçekten geçerli olup
    olmadığını kontrol etmez. Bu görev app.py
    tarafından Telegram API ile yapılmalıdır.
    """
    return (
        isinstance(token, str)
        and bool(token.strip())
        and len(token.strip()) <= 256
    )


# ========================================
# TOKEN KAYDET
# ========================================

def save_token(token: str) -> None:
    """
    Telegram bot tokenını local config dosyasına güvenli
    ve atomik şekilde kaydeder.

    Yeni veri önce aynı klasörde geçici dosyaya yazılır.
    Yazma işlemi başarıyla tamamlandıktan sonra mevcut
    config.json atomik olarak değiştirilir.
    """

    if not isinstance(token, str):
        raise TypeError("Token string olmalıdır.")

    token = token.strip()

    if not token:
        raise ValueError("Token boş bırakılamaz.")

    if len(token) > 256:
        raise ValueError("Token çok uzun.")

    _ensure_data_dir()

    data = {
        TOKEN_KEY: token
    }

    temp_file: Optional[Path] = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=DATA_DIR,
            prefix=".config_",
            suffix=".tmp",
            delete=False
        ) as file:

            temp_file = Path(file.name)

            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4
            )

            file.flush()
            os.fsync(file.fileno())

        os.replace(
            temp_file,
            TOKEN_FILE
        )

        temp_file = None

    except Exception:
        if temp_file is not None:
            try:
                temp_file.unlink(missing_ok=True)
            except OSError:
                pass

        raise


# ========================================
# TOKEN OKU
# ========================================

def get_token() -> Optional[str]:
    """
    Kaydedilmiş tokenı döndürür.

    Aşağıdaki durumlarda None döndürülür:
    - config.json yoksa
    - dosya okunamıyorsa
    - dosya aşırı büyükse
    - JSON bozuksa
    - JSON bir object değilse
    - token alanı yoksa
    - token string değilse
    - token boşsa
    """

    if not TOKEN_FILE.exists():
        return None

    try:
        # Dosya boyutunu kontrol et.
        file_size = TOKEN_FILE.stat().st_size

        if file_size > MAX_CONFIG_SIZE:
            return None

        with TOKEN_FILE.open(
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

    except (
        OSError,
        json.JSONDecodeError
    ):
        return None

    if not isinstance(data, dict):
        return None

    token = data.get(TOKEN_KEY)

    if not _is_valid_token_value(token):
        return None

    return token.strip()


# ========================================
# TOKEN SİL
# ========================================

def delete_token() -> bool:
    """
    Kayıtlı token dosyasını siler.

    Dosya yoksa False döndürür.
    Başarıyla silinirse True döndürür.

    Silme işlemi başarısız olursa OSError yükseltir.
    """

    try:
        TOKEN_FILE.unlink()

    except FileNotFoundError:
        return False

    except OSError as error:
        raise OSError(
            "Token dosyası silinemedi."
        ) from error

    return True
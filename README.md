# İTOBOT Grant Tracker

**İTOBOT Grant Tracker**, İTOBOT robotik takımının Telegram botunu hızlı ve güvenli şekilde yapılandırmak için geliştirilmiş, Flask tabanlı bir token kurulum uygulamasıdır.

Uygulama, Telegram Bot Token'ını kullanıcıdan alır, Telegram Bot API üzerinden doğrular ve token'ı güvenli şekilde yerel yapılandırma dosyasına kaydeder.

> Token'lar GitHub'a, kaynak koduna veya herhangi bir uzak servise gönderilmez.

---

## Özellikler

### Token Yönetimi

* Telegram Bot Token kurulumu
* Telegram Bot API üzerinden gerçek token doğrulaması
* Telegram Bot Token format kontrolü
* Token'ın yerel olarak saklanması
* Token değiştirme
* Kayıtlı token'ı silme
* Token göster / gizle özelliği
* Atomik config dosyası yazımı

### Güvenlik

* CSRF koruması
* Rate limiting
* Content Security Policy (CSP)
* Güvenlik HTTP header'ları
* Maksimum request boyutu sınırı
* Token'ın Git'e dahil edilmesini engelleyen `.gitignore`
* Hardcoded secret kullanılmaması
* Telegram API bağlantılarında timeout kontrolü
* Hatalı ve geçersiz isteklerin kontrol edilmesi

### Test

* Pytest tabanlı test altyapısı
* Uygulama route testleri
* Token doğrulama testleri
* Token kayıt ve silme testleri
* CSRF testleri
* Rate limit testleri
* Hatalı input testleri

Mevcut test durumu:

```text
83 passed
```

---

## Kullanılan Teknolojiler

| Teknoloji  | Kullanım                    |
| ---------- | --------------------------- |
| Python     | Ana programlama dili        |
| Flask      | Web uygulaması              |
| Requests   | Telegram Bot API bağlantısı |
| Pytest     | Test altyapısı              |
| HTML5      | Arayüz                      |
| CSS3       | Tasarım                     |
| JavaScript | Etkileşim ve API istekleri  |

---

## Proje Yapısı

```text
itobot-token-setup/
│
├── app.py
├── token_manager.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── templates/
│   ├── setup.html
│   └── success.html
│
├── static/
│   ├── css/
│   │   ├── base.css
│   │   ├── setup.css
│   │   └── success.css
│   │
│   └── js/
│       ├── setup.js
│       └── success.js
│
├── test_app.py
└── test_token_manager.py
```

### Yerel yapılandırma

Uygulama çalışırken token bilgisi:

```text
data/config.json
```

dosyasında tutulur.

`data/` klasörü `.gitignore` tarafından Git takibinin dışında bırakılmıştır.

---

## Kurulum

### 1. Repository'yi klonlayın

```bash
git clone https://github.com/EmirhannCoskun/itobot-token-setup.git
cd itobot-token-setup
```

### 2. Sanal ortam oluşturun

Windows:

```powershell
python -m venv venv
```

Sanal ortamı aktif edin:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Bağımlılıkları yükleyin

```powershell
pip install -r requirements.txt
```

---

## Yapılandırma

Uygulama Flask tarafından çalıştırılır.

Güvenlik amacıyla Flask secret key'in ortam değişkeninden verilmesi önerilir.

PowerShell:

```powershell
$env:FLASK_SECRET_KEY="guclu-bir-secret-key"
```

Ardından uygulamayı başlatabilirsiniz:

```powershell
python app.py
```

Uygulama varsayılan olarak:

```text
http://127.0.0.1:5000
```

adresinde çalışır.

---

## Token Kurulum Akışı

```text
┌──────────────────────┐
│   Token Kurulum      │
│       Ekranı         │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Token Format Kontrolü│
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Telegram Bot API     │
│       getMe          │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Token Başarılı mı?   │
└───────┬───────┬──────┘
        │       │
       Hayır   Evet
        │       │
        ▼       ▼
     Hata    config.json
     mesajı    kaydı
                │
                ▼
       ┌────────────────┐
       │ Başarı Sayfası │
       └────────────────┘
```

---

## Token Değiştirme

Başarı ekranındaki `Tokenı Değiştir` butonu kullanıcıyı tekrar token giriş ekranına yönlendirir.

Yeni token:

1. Format kontrolünden geçer.
2. Telegram Bot API üzerinden doğrulanır.
3. Doğrulama başarılıysa mevcut token'ın yerine kaydedilir.

Eski token, yeni token başarıyla doğrulanmadan silinmez.

---

## Token Silme

Başarı ekranında bulunan `Tokenı Sil` butonu kayıtlı tokenı yerel yapılandırmadan kaldırır.

Silme işlemi:

* CSRF kontrolünden geçer.
* Kayıtlı tokenı siler.
* İşlem başarılı olduğunda kullanıcıyı kurulum ekranına yönlendirir.

---

## Testleri Çalıştırma

Projede Pytest kullanılmaktadır.

Tüm testleri çalıştırmak için:

```powershell
pytest
```

Beklenen sonuç:

```text
83 passed
```

Daha ayrıntılı çıktı için:

```powershell
pytest -v
```

---

## API Endpoint'leri

| Method | Endpoint        | Açıklama                    |
| ------ | --------------- | --------------------------- |
| `GET`  | `/`             | Ana / kurulum ekranı        |
| `POST` | `/save-token`   | Token doğrulama ve kaydetme |
| `GET`  | `/success`      | Başarılı kurulum ekranı     |
| `GET`  | `/change-token` | Token değiştirme ekranı     |
| `POST` | `/delete-token` | Kayıtlı tokenı silme        |

---

## Güvenlik Notu

Bu proje özellikle Telegram Bot Token'ının kaynak koduna dahil edilmemesi amacıyla tasarlanmıştır.

### Yapılmaması gerekenler

* Token'ı `app.py` içerisine yazmayın.
* Token'ı JavaScript dosyasına koymayın.
* Token'ı HTML içerisine koymayın.
* `data/config.json` dosyasını Git'e eklemeyin.
* `.env` veya benzeri secret dosyalarını commit etmeyin.

### Yapılması gerekenler

* Token'ı uygulamanın kurulum ekranından girin.
* Secret değerlerini environment variable olarak sağlayın.
* `.gitignore` dosyasının `data/` ve secret dosyalarını dışladığından emin olun.

---

## Repository

[GitHub Repository](https://github.com/EmirhannCoskun/itobot-token-setup)

# Legionella Eğitim Portalı (Çalışan Sistem) — İnternet Erişimli (10 Asistan)

Bu paket, 10 asistan için hazır kullanıcıları olan, girişli bir eğitim portalıdır:
- Ders notları (HTML/PDF bağlantıları)
- 50+ vaka bankası (listeleme)
- Online sınav (otomatik puanlama)
- Asistan performans sayfası (kendi skorları)
- Admin paneli (tüm sonuçlar, kullanıcı yönetimi + CSV dışa aktarım)

## 1) Hızlı Çalıştırma (Windows / Linux / macOS)
1. Python 3.10+ kurulu olsun.
2. Klasörde terminal aç:
   ```bash
   pip install -r requirements.txt
   python app.py
   ```
3. Tarayıcı:
   - http://127.0.0.1:5000

## 2) İnternete Açma (VPS / Sunucu)
> Güvenli ve standart yöntem: Gunicorn + Nginx (önerilir).

### 2.1 Gunicorn ile çalıştır
```bash
pip install -r requirements.txt
gunicorn -w 2 -b 0.0.0.0:8000 app:app
```
Tarayıcı: http://SUNUCU_IP:8000

### 2.2 Nginx reverse proxy (öneri)
Nginx ile 80/443'ten 8000'e yönlendir.
SSL için Let's Encrypt kullanılabilir (kurum IT politikalarına göre).

## 3) Varsayılan Kullanıcılar
### Admin
- kullanıcı: admin
- şifre: Admin!2345

### 10 Asistan
- asistan01 / Asistan!2345
- asistan02 / Asistan!2345
...
- asistan10 / Asistan!2345

> İlk iş: admin ile girip şifreleri değiştirin.

## 4) Veritabanı
SQLite kullanır: `data/app.db`
- Yedekleme: bu dosyayı kopyalamanız yeterli.

## 5) Dosya Yapısı
- app.py : ana uygulama
- templates/ : HTML arayüzleri
- static/ : basit CSS
- data/ : sqlite DB + vaka bankası JSON

## 6) Akreditasyon için kanıt üretimi
Admin panelinden:
- Tüm sınav sonuçları listesi
- CSV export
- Kullanıcı bazlı performans

---
Not: Bu bir demo/kurum içi eğitim sistemi iskeletidir. Kurumsal güvenlik (SSL, güçlü parola, IP kısıtları) IT ile birlikte planlanmalıdır.

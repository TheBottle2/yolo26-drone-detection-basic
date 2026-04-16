# YOLO26 Drone Detection Basic

Bu proje, kameradan alınan görüntüde drone tespiti yapıp hedefi yatay eksende
takip eden bir sistemdir. Tespit ve karar verme bilgisayarda (Python + YOLO),
motor sürme ve mesafe ölçümü ise Arduino tarafında çalışır.

## Projenin Amacı

- Drone benzeri hedefleri gerçek zamanlı tespit etmek
- Hedef ekran merkezinden sapınca motoru sağ/sol döndürerek hizalamak
- Web arayüzünden canlı görüntü, sensör verisi ve kontrol sunmak

## Mimari (3 Katman)

1. Arduino katmanı (`src/main.cpp`)
- 28BYJ-48 step motoru sürer (ULN2003)
- HC-SR04 ile periyodik mesafe ölçer
- Seri porttan komut alır, mesafeyi geri gönderir

2. Python köprü katmanı (`bridge.py`)
- Kameradan görüntü alır
- YOLO modeli ile hedefi tespit eder
- Hedef hatasına göre orantılı adım hesabı yapar
- Arduino'ya seri komut yollar
- Tarayıcıya WebSocket ile görüntü + telemetri yayınlar

3. Web arayüzü (`index.html`)
- `ws://localhost:8765` üzerinden veri alır
- Canlı kamera görüntüsünü gösterir
- Manuel/Takip modu arasında geçiş yapar
- Manuel modda sağ/sol komut gönderir

## Komut ve Veri Protokolü

PC -> Arduino:
- `R:15` : sağa 15 adım
- `L:8`  : sola 8 adım
- `S`    : dur

Arduino -> PC:
- `D:XX` : mesafe (cm)

Not: Satır sonu `\n` ile gönderilir.

## Çalıştırma Mantığı

1. Python tarafı her karede hedefin merkezini bulur.
2. Hedef merkezi ile ekran merkezi arasındaki piksel farkı (`error`) hesaplanır.
3. `error`, `DEADZONE_PX` dışındaysa adım sayısı orantılı belirlenir:
- Küçük hata -> az adım (`PROP_MIN_STEP`)
- Büyük hata -> çok adım (`PROP_MAX_STEP`)
4. Uygun komut (`R`, `L`, `S`) Arduino'ya gönderilir.
5. Arduino motoru hareket ettirir ve belirli aralıklarla mesafe bilgisini yollar.
6. Web arayüzü canlı görüntü, komut, hedef bilgisi ve mesafeyi anlık gösterir.

## Kurulum

### 1) Gereksinimler

- Python 3.9+
- PlatformIO (VS Code eklentisi veya `pio` CLI)
- Arduino Uno
- 28BYJ-48 + ULN2003
- HC-SR04
- Kamera

### 2) Python paketleri

Proje kökünde terminal açıp:

```bash
pip install ultralytics opencv-python pyserial websockets
```

### 3) Yapılandırma (`config.py`)

Aşağıdaki alanları kendi ortamına göre güncelle:

- `MODEL_PATH`: Eğitilmiş model dosyası (`best.pt`) yolu
- `CAMERA_INDEX`: Kamera numarası (genelde `0`)
- `SERIAL_FALLBACK_PORT`: Gerekirse port adı
  - Windows örnek: `COM3`
  - Linux örnek: `/dev/ttyUSB0`
- `WS_HOST`, `WS_PORT`: WebSocket adresi

### 4) Arduino kodunu yükleme

`platformio.ini` dosyası `uno` ortamını kullanır. Kod yüklemek için:

```bash
pio run -t upload
```

Gerekirse `platformio.ini` içinde upload portu ayrıca belirtilebilir.

### 5) Köprüyü çalıştırma

```bash
python bridge.py
```

Konsolda model, seri bağlantı ve WebSocket başlatma mesajlarını görmelisin.

### 6) Arayüzü açma

- Doğrudan `index.html` dosyasını tarayıcıda aç
veya
- Basit bir yerel sunucu ile aç:

```bash
python -m http.server 5500
```

Sonra tarayıcıdan `http://localhost:5500` adresine git.

## Kullanım

- MANUEL mod:
  - Arayüzde sol/sağ tuşlarına basılı tutarak motoru döndür
  - Bırakınca `S` komutu ile durur

- TAKİP modu:
  - YOLO tespiti aktif olur
  - Sistem hedefe göre otomatik sağ/sol düzeltme yapar

## Önemli Dosyalar

- `bridge.py`: Ana uygulama akışı
- `config.py`: Tüm parametreler
- `src/main.cpp`: Arduino firmware
- `index.html`: İzleme ve kontrol paneli
- `best.pt`: Eğitilmiş model
- `args (1).yaml`: Eğitim parametre çıktısı

## Hızlı Sorun Giderme

- Kamera açılmıyor:
  - `CAMERA_INDEX` değerini değiştir

- Arduino bağlanmıyor:
  - Kablo/port kontrol et
  - `SERIAL_FALLBACK_PORT` değerini doğru porta ayarla

- Model yüklenmiyor:
  - `MODEL_PATH` yolunun doğru olduğundan emin ol

- Arayüzde bağlantı yok yazıyor:
  - `bridge.py` çalışıyor olmalı
  - `WS_HOST/WS_PORT` ile arayüzdeki adres aynı olmalı
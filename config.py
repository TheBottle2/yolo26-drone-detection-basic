# config.py — Turret Takip Sistemi Ayarları

# === KAMERA ===
CAMERA_INDEX = 0

# === YOLO26 ===
# Modeli Drive'dan indirince yolu güncelle
# Eğitim bittikten sonra Drive'dan indirilen dosyaların yolunu buraya yaz
# Notebook'un son hücresi tam yolu gösterecek
MODEL_PATH = "/home/luna/Belgeler/PlatformIO/Projects/Drone_Takip/best.pt"
YAML_PATH  = "/home/luna/Belgeler/PlatformIO/Projects/Drone_Takip/data.yaml"
CONFIDENCE  = 0.5
# None = yaml'daki ilk sınıf otomatik seçilir
# Belirli sınıf için örnek: TARGET_CLASS = "drone"
TARGET_CLASS = None

# === SERİAL (Arduino) — port otomatik bulunur ===
SERIAL_BAUDRATE    = 9600
SERIAL_TIMEOUT     = 1
SERIAL_FALLBACK_PORT = "/dev/ttyUSB0"

# === WEBSOCKET ===
WS_HOST = "localhost"
WS_PORT = 8765

# === DONANIM MODU ===
# "test"  → 28BYJ-48 + ULN2003 (şu anki)
# "final" → NEMA17 + MG90S Servo (ileride)
HARDWARE_MODE = "test"

# === PLATFORM — TEST (28BYJ-48) ===
# 28BYJ-48: yarım adım modunda 4096 adım = 360°
# 180° tarama için 2048 adım yeterli
BYJ_STEPS_PER_REV = 4096
BYJ_STEP_DELAY    = 0.001   # saniye — düşürürsen hız artar, çok düşürme

# Pan takip hassasiyeti
# Ekranın ortasından bu kadar piksel sağa/sola çıkınca motor döner
DEADZONE_PX = 40            # piksel cinsinden ölü bölge

# Proportional kontrol adım aralığı
# Hata küçükse MIN_STEP, büyükse MAX_STEP kadar adım atar
PROP_MIN_STEP = 2           # Hedefe yakınken minimum adım
PROP_MAX_STEP = 20          # Hedefe uzakken maksimum adım

# === PLATFORM — FINAL (NEMA17 + Servo) ===
# Aktif değil, sadece referans
NEMA_STEPS_PER_REV = 3200   # A4988 yarım adım modunda
SERVO_MIN   = 0
SERVO_MAX   = 180
SERVO_CENTER = 90
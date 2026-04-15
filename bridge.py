# bridge.py — Drone Takip Köprüsü (Proportional Kontrol)
# YOLO26 (PC kamera) → Serial (Arduino) → WebSocket (tarayıcı)

import asyncio
import base64
import json
import threading
import time
import serial
import serial.tools.list_ports
import cv2
import websockets
from ultralytics import YOLO
from config import *

# ── Global durum ──────────────────────────────────────────────
state = {
    "mode":      "manual",   # "manual" | "track"
    "command":   "S",        # Son gönderilen komut
    "steps":     0,          # Son gönderilen adım sayısı
    "distance":  -1,         # HC-SR04 (cm)
    "target":    None,       # Tespit edilen hedef
    "frame_b64": None,       # Tarayıcıya gönderilecek frame
    "connected_clients": set(),
}

arduino = None
model   = None

# ── Proportional adım hesapla ─────────────────────────────────

def calc_steps(error_px, frame_width):
    """
    Piksel hatasını adım sayısına çevir.
    Hata büyükse çok adım, küçükse az adım.
    """
    # Hata oranı (0.0 - 0.5 arası, ekranın yarısı max)
    ratio = abs(error_px) / (frame_width / 2)
    ratio = min(ratio, 1.0)

    # Adım sayısı: MIN_STEP ile MAX_STEP arasında orantılı
    steps = int(PROP_MIN_STEP + ratio * (PROP_MAX_STEP - PROP_MIN_STEP))
    return steps

# ── Arduino Bağlantısı ────────────────────────────────────────

def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = (p.description or "").lower()
        if any(k in desc for k in ["arduino", "ch340", "ch341", "uart", "usb serial", "esp32", "cp210"]):
            print(f"[Serial] Bulundu: {p.device} ({p.description})")
            return p.device

    candidates = ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0", "/dev/ttyACM1"]
    for c in candidates:
        try:
            s = serial.Serial(c, SERIAL_BAUDRATE, timeout=SERIAL_TIMEOUT)
            s.close()
            print(f"[Serial] Fallback: {c}")
            return c
        except:
            continue

    print(f"[Serial] Port bulunamadı, fallback: {SERIAL_FALLBACK_PORT}")
    return SERIAL_FALLBACK_PORT

def connect_arduino():
    global arduino
    port = find_arduino_port()
    try:
        arduino = serial.Serial(port, SERIAL_BAUDRATE, timeout=SERIAL_TIMEOUT)
        time.sleep(2)
        print(f"[Serial] Bağlandı: {port}")
    except Exception as e:
        print(f"[Serial] Hata: {e}")
        arduino = None

def send_command(cmd, steps=0):
    """Arduino'ya komut gönder. R/L için adım sayısı eklenir."""
    global arduino
    if arduino and arduino.is_open:
        try:
            if cmd in ("R", "L"):
                msg = f"{cmd}:{steps}\n"
            else:
                msg = "S\n"
            arduino.write(msg.encode())
            state["command"] = cmd
            state["steps"]   = steps
        except Exception as e:
            print(f"[Serial] Gönderme hatası: {e}")

# ── Arduino Okuma ─────────────────────────────────────────────

def arduino_reader():
    while True:
        if arduino and arduino.is_open:
            try:
                line = arduino.readline().decode("utf-8", errors="ignore").strip()
                if line.startswith("D:"):
                    val = line[2:]
                    state["distance"] = int(val) if val.lstrip("-").isdigit() else -1
            except:
                pass
        time.sleep(0.01)

# ── Kamera + YOLO ─────────────────────────────────────────────

def camera_loop():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("[Kamera] Açılamadı!")
        return

    print("[Kamera] Başladı.")

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.05)
            continue

        h, w = frame.shape[:2]
        center_x = w // 2
        detected = False

        if state["mode"] == "track":
            results = model.predict(
                source=frame,
                conf=CONFIDENCE,
                verbose=False,
                stream=False
            )

            for r in results:
                boxes = r.boxes
                if boxes is None or len(boxes) == 0:
                    continue

                best = max(boxes, key=lambda b: float(b.conf[0]))
                cls_name = model.names[int(best.cls[0])]
                if TARGET_CLASS and cls_name != TARGET_CLASS:
                    continue

                detected = True

                x1, y1, x2, y2 = map(int, best.xyxy[0])
                bx = (x1 + x2) // 2
                by = (y1 + y2) // 2

                state["target"] = {
                    "x":    bx / w,
                    "y":    by / h,
                    "w":    (x2 - x1) / w,
                    "h":    (y2 - y1) / h,
                    "conf": round(float(best.conf[0]), 2),
                    "cls":  cls_name,
                }

                # Çerçeve çiz
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{cls_name} {state['target']['conf']}",
                            (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (0, 255, 0), 2)
                cv2.circle(frame, (bx, by), 5, (0, 0, 255), -1)

                # Hata hesapla
                error = bx - center_x

                if error > DEADZONE_PX:
                    steps = calc_steps(error, w)
                    send_command("R", steps)
                elif error < -DEADZONE_PX:
                    steps = calc_steps(error, w)
                    send_command("L", steps)
                else:
                    send_command("S")

                break

            if not detected:
                state["target"] = None
                send_command("S")

        else:
            state["target"] = None
            send_command("S")

        # Yardımcı çizgiler
        cv2.line(frame, (center_x - DEADZONE_PX, 0),
                 (center_x - DEADZONE_PX, h), (255, 255, 0), 1)
        cv2.line(frame, (center_x + DEADZONE_PX, 0),
                 (center_x + DEADZONE_PX, h), (255, 255, 0), 1)
        cv2.line(frame, (center_x, 0), (center_x, h), (0, 200, 200), 1)

        cv2.putText(frame, f"MOD: {state['mode'].upper()}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 255, 0) if state["mode"] == "track" else (0, 165, 255), 2)

        if state["steps"] > 0:
            cv2.putText(frame, f"ADIM: {state['steps']}",
                        (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (0, 255, 224), 2)

        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        state["frame_b64"] = base64.b64encode(buf).decode("utf-8")

    cap.release()

# ── WebSocket ─────────────────────────────────────────────────

async def ws_handler(websocket):
    state["connected_clients"].add(websocket)
    print(f"[WS] Bağlandı: {websocket.remote_address}")
    try:
        async for raw in websocket:
            try:
                msg = json.loads(raw)
                action = msg.get("action")

                if action == "set_mode":
                    new_mode = msg.get("mode", "manual")
                    if new_mode in ("manual", "track"):
                        state["mode"] = new_mode
                        print(f"[WS] Mod: {new_mode}")

                elif action == "manual_command":
                    if state["mode"] == "manual":
                        cmd = msg.get("cmd", "S")
                        if cmd in ("R", "L"):
                            send_command(cmd, PROP_MAX_STEP)
                        elif cmd == "S":
                            send_command("S")

            except json.JSONDecodeError:
                pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        state["connected_clients"].discard(websocket)

async def broadcast_loop():
    while True:
        if state["connected_clients"] and state["frame_b64"]:
            payload = json.dumps({
                "frame":    state["frame_b64"],
                "mode":     state["mode"],
                "command":  state["command"],
                "steps":    state["steps"],
                "distance": state["distance"],
                "target":   state["target"],
            })
            dead = set()
            for ws in state["connected_clients"].copy():
                try:
                    await ws.send(payload)
                except:
                    dead.add(ws)
            state["connected_clients"] -= dead
        await asyncio.sleep(0.05)

# ── Ana Giriş ─────────────────────────────────────────────────

async def main():
    global model

    print("[YOLO26] Model yükleniyor...")
    model = YOLO(MODEL_PATH)
    print(f"[YOLO26] Hazır. Sınıflar: {list(model.names.values())}")

    print("[Serial] Arduino aranıyor...")
    connect_arduino()

    t_arduino = threading.Thread(target=arduino_reader, daemon=True)
    t_arduino.start()

    t_camera = threading.Thread(target=camera_loop, daemon=True)
    t_camera.start()

    print(f"[WS] Sunucu başlıyor: ws://{WS_HOST}:{WS_PORT}")
    async with websockets.serve(ws_handler, WS_HOST, WS_PORT):
        await broadcast_loop()

if __name__ == "__main__":
    asyncio.run(main())
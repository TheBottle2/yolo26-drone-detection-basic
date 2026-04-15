// main.cpp — Drone Takip Sistemi (Non-blocking Serial)
// Protokol:
//   PC → Arduino: "R:15\n" sağa 15 adım, "L:8\n" sola 8 adım, "S\n" dur
//   Arduino → PC: "D:XX\n" mesafe (cm)

#include <Arduino.h>

// === BYJ-48 Pinleri ===
#define IN1 8
#define IN2 9
#define IN3 10
#define IN4 11

// === HC-SR04 Pinleri ===
#define TRIG 6
#define ECHO 7

// === Ayarlar ===
#define STEP_DELAY    2     // ms
#define DISTANCE_INT  250   // ms — mesafe ölçüm aralığı

// Yarım adım dizisi
const int stepSeq[8][4] = {
  {1,0,0,0},
  {1,1,0,0},
  {0,1,0,0},
  {0,1,1,0},
  {0,0,1,0},
  {0,0,1,1},
  {0,0,0,1},
  {1,0,0,1}
};

int stepIndex = 0;
unsigned long lastDistanceTime = 0;

// Non-blocking serial buffer
String serialBuf = "";

// === Motor Fonksiyonları ===

void motorOff() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
}

void moveSteps(int count, bool right) {
  for (int i = 0; i < count; i++) {
    stepIndex = right ? (stepIndex + 1) % 8 : (stepIndex + 7) % 8;
    digitalWrite(IN1, stepSeq[stepIndex][0]);
    digitalWrite(IN2, stepSeq[stepIndex][1]);
    digitalWrite(IN3, stepSeq[stepIndex][2]);
    digitalWrite(IN4, stepSeq[stepIndex][3]);
    delay(STEP_DELAY);
  }
  motorOff();
}

// === HC-SR04 ===

long readDistance() {
  // Temiz tetik sinyali
  digitalWrite(TRIG, LOW);
  delayMicroseconds(4);
  digitalWrite(TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);

  // Echo ölçümü — 30ms timeout (~510cm, fazlasıyla yeterli)
  long duration = pulseIn(ECHO, HIGH, 30000);
  if (duration == 0) return -1;

  // cm hesaplama: standart formül
  return duration / 58;
}

// === Komut İşle ===

void processCommand(String cmd) {
  cmd.trim();

  if (cmd == "S") {
    motorOff();

  } else if (cmd.startsWith("R:")) {
    int count = cmd.substring(2).toInt();
    if (count > 0 && count <= 100) moveSteps(count, true);

  } else if (cmd.startsWith("L:")) {
    int count = cmd.substring(2).toInt();
    if (count > 0 && count <= 100) moveSteps(count, false);
  }
}

// === Setup ===

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(10); // Serial timeout çok düşük tut

  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);

  motorOff();
  Serial.println("READY");
}

// === Loop ===

void loop() {
  // Non-blocking serial okuma
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') {
      if (serialBuf.length() > 0) {
        processCommand(serialBuf);
        serialBuf = "";
      }
    } else {
      serialBuf += c;
      // Buffer taşmasını önle
      if (serialBuf.length() > 20) serialBuf = "";
    }
  }

  // Mesafe ölçümü
  unsigned long now = millis();
  if (now - lastDistanceTime >= DISTANCE_INT) {
    lastDistanceTime = now;
    long dist = readDistance();
    Serial.print("D:");
    Serial.println(dist);
  }
}
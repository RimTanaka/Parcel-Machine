#include <Arduino.h>
#include <Servo.h>
#include <WiFiNINA.h>
#include <UniversalTelegramBot.h>

#define LED_PIN 13 // Пин светодиодной индикации
#define DOOR_COUNT 10 // Количество дверей в почтомате

// Параметры Wi-Fi и Telegram
#define WIFI_SSID "your_wifi_ssid"
#define WIFI_PASS "your_wifi_password"
#define TELEGRAM_BOT_TOKEN "your_telegram_bot_token"

// Параметры для управления почтоматом
#define OPEN_TIME 600000 // Время открытия двери в миллисекундах (10 минут)
#define SERVO_PIN 9 // Пин, к которому подключен сервопривод

Servo servo;

WiFiClient client;
UniversalTelegramBot bot(TELEGRAM_BOT_TOKEN, client);

unsigned long lastOpenTime = 0; // Время последнего открытия двери
bool doorLocked[DOOR_COUNT] = {false}; // Массив, указывающий, заблокирована ли дверь

void setup() {
  Serial.begin(9600);
  pinMode(LED_PIN, OUTPUT);
  servo.attach(SERVO_PIN);

  connectToWiFi();
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    if (Serial.available() > 0) {
      String command = Serial.readStringUntil('\n');
      processCommand(command);
    }
  } else {
    connectToWiFi();
  }
}

void connectToWiFi() {
  Serial.println("Connecting to Wi-Fi...");
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 5) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
  } else {
    Serial.println("\nUnable to connect to Wi-Fi. Please check your credentials.");
  }
}

// Протокол взаимодействия с ТГ ботом
void processCommand(String command) {
  int doorNumber = command.toInt();

  if (doorNumber >= 1 && doorNumber <= DOOR_COUNT) {
    if (!doorLocked[doorNumber - 1] && (millis() - lastOpenTime) > OPEN_TIME) {
      openDoor(doorNumber);
      lastOpenTime = millis();
    } else {
      bot.sendMessage("chat_id", "Дверь уже открыта или заблокирована. Попробуйте позже.");
    }
  } else {
    bot.sendMessage("chat_id", "Некорректный номер двери.");
  }
}

void openDoor(int doorNumber) {
  digitalWrite(LED_PIN, HIGH);
  servo.write(90); // Управление сервоприводом для открытия двери
  delay(2000); // Задержка для открытия двери
  servo.write(0); // Возврат сервопривода в начальное положение
  digitalWrite(LED_PIN, LOW);

  doorLocked[doorNumber - 1] = true; // Блокировка двери после открытия
  delay(600000); // Пауза перед разблокировкой двери (10 минут)
  doorLocked[doorNumber - 1] = false; // Разблокировка двери
}

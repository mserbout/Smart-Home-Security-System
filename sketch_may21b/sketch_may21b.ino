#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include "DHTesp.h"
#include <time.h>
#include <ArduinoJson.h>

WiFiClient wClient;
PubSubClient mqtt_client(wClient);
DHTesp dht;

int PIN_MOTION_SENSOR = 4;
int PIN_SPEAKER = 12;
int PIN_RED_LED = 13;
int PIN_GREEN_LED = 15;
bool alarm;
int number_detection = 0;
float humidity;
float temperature;
String status;
String current_datetime;
StaticJsonDocument<200> doc;

// Update these with values suitable for your network.
const char* ssid = "WIN-LAOM7JEF5R6 9062";
const char* password = "Lz0492&6";
const char* mqtt_server = "35.192.204.119";

String ID_PLACA;
String topic_PUB_telegram = "data/telegram/Malaga";
String topic_PUB_google = "data/google/Malaga";
String topic_SUB_alarm = "cmd/alarm/Malaga"; // Subscription topic
String topic_SUB_status = "cmd/status/Malaga"; // Subscription topic

void conecta_wifi() {goog
  Serial.println("Connecting to " + String(ssid));
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(200);
    Serial.print(".");
  }
  Serial.println("WiFi connected, IP address: " + WiFi.localIP().toString());
}

void conecta_mqtt() {
  while (!mqtt_client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (mqtt_client.connect(ID_PLACA.c_str())) {
      Serial.println(" connected to broker: " + String(mqtt_server));
      // Subscribe to the topic
      mqtt_client.subscribe(topic_SUB_alarm.c_str());
      Serial.println("Subscribed to topic: " + topic_SUB_alarm);

      mqtt_client.subscribe(topic_SUB_status.c_str());
      Serial.println("Subscribed to topic: " + topic_SUB_status);
    } else {
      Serial.println("ERROR:" + String(mqtt_client.state()) + " retrying in 5s");
      delay(5000);
    }
  }
}

String getFormattedTimestamp() {
  time_t now = time(nullptr);
  struct tm* p_tm = localtime(&now);
  char timestamp_string[20]; // YYYY-MM-DD HH:MM:SS format
  snprintf(timestamp_string, sizeof(timestamp_string), "%04d-%02d-%02d %02d:%02d:%02d", p_tm->tm_year + 1900, p_tm->tm_mon + 1, p_tm->tm_mday,
           p_tm->tm_hour, p_tm->tm_min, p_tm->tm_sec);
  return String(timestamp_string);
}

void callback(char* topic, byte* payload, unsigned int length) {
  Serial.println("Message received on topic: " + String(topic));
  Serial.println("Payload: ");
  
  char messageBuffer[length + 1]; // Create a buffer to store the payload
  memcpy(messageBuffer, payload, length); // Copy the payload into the buffer
  messageBuffer[length] = '\0'; // Null-terminate the buffer
  
  String message = String(messageBuffer); // Create a String from the buffer

  Serial.println(message);

  if (String(topic) == topic_SUB_alarm) {
    if (message[0] == '1') {
      Serial.println("Alarm is on!!");
      digitalWrite(PIN_GREEN_LED, HIGH);
      digitalWrite(PIN_RED_LED, LOW);
      alarm = true;
    } else {
      Serial.println("Alarm is off!!");
      digitalWrite(PIN_GREEN_LED, LOW);
      digitalWrite(PIN_RED_LED, HIGH);
      alarm = false;
    }
  }

  if (String(topic) == topic_SUB_status) {
    humidity = dht.getHumidity();
    temperature = dht.getTemperature();
    if (alarm) {
      status = "Alarm ON";
    } else {
      status = "Alarm OFF";
    }
    current_datetime = getFormattedTimestamp();
    doc["temperature"] = temperature;
    doc["humidity"] = humidity;
    doc["alarm"] = status;
    doc["detection"] = number_detection;
    doc["time"] = current_datetime;
    
    String house_status;
    serializeJson(doc, house_status);
    Serial.println();
    Serial.println("Topic   : " + topic_PUB_telegram);
    Serial.println("Payload : " + house_status);
    mqtt_client.publish(topic_PUB_telegram.c_str(), house_status.c_str());

    number_detection = 0;
  }
  // Handle the received message here
}

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("Setup started...");
  ID_PLACA = "ESP_" + String(ESP.getChipId());
  conecta_wifi();
  mqtt_client.setServer(mqtt_server, 1883);
  mqtt_client.setBufferSize(512);
  mqtt_client.setCallback(callback); // Set callback function
  conecta_mqtt();
  Serial.println("Device ID: " + ID_PLACA);
  Serial.println("Publication Topic: " + topic_PUB_telegram);
  Serial.println("Subscription Topic: " + topic_SUB_alarm + " " + topic_SUB_status);
  Serial.println("Setup finished in " + String(millis()) + " ms");
  dht.setup(5, DHTesp::DHT11);
  pinMode(PIN_GREEN_LED, OUTPUT);
  digitalWrite(PIN_GREEN_LED, LOW);
  pinMode(PIN_RED_LED, OUTPUT);
  digitalWrite(PIN_RED_LED, LOW);
  // Set up NTP
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
}

unsigned long last_message = 0;

void loop() {
  if (!mqtt_client.connected()) conecta_mqtt();
  mqtt_client.loop();
  unsigned long now = millis();

  bool sensorValue = digitalRead(PIN_MOTION_SENSOR);
  Serial.print("Sensor Value: ");
  Serial.println(sensorValue);
  delay(1000);

  if (alarm) {
    if (sensorValue) {
      tone(PIN_SPEAKER, 440);
      delay(1000);

      number_detection++;
      noTone(PIN_SPEAKER);
      delay(1000);
    }
  }

  if (now - last_message >= 100000) {
    humidity = dht.getHumidity();
    temperature = dht.getTemperature();
    last_message = now;
    String current_datetime = getFormattedTimestamp();
    doc["temperature"] = temperature;
    doc["humidity"] = humidity;
    doc["Alarm Status"] = sensorValue;
    doc["Number Detection"] = number_detection;
    doc["longitude"] = 12.0;
    doc["latitude"] = 50.0;
    doc["time"] = current_datetime;

    String mensaje;
    serializeJson(doc, mensaje);
    Serial.println();
    Serial.println("Topic   : " + topic_PUB_google);
    Serial.println("Payload : " + mensaje);
    mqtt_client.publish(topic_PUB_google.c_str(), mensaje.c_str());
  }
}

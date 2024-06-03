#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include "DHTesp.h"
#include <time.h>
#include <ArduinoJson.h>
#include <NTPClient.h>
#include <WiFiUdp.h>

WiFiClient wClient;
PubSubClient mqtt_client(wClient);
DHTesp dht;

WiFiUDP ntpUDP;
const long utcOffsetInSeconds = 7200;
NTPClient timeClient(ntpUDP, "pool.ntp.org", utcOffsetInSeconds);

int PIN_MOTION_SENSOR = 4;
int PIN_SPEAKER = 12;
int PIN_RED_LED = 13;
int PIN_GREEN_LED = 15;
bool alarm = false;
int number_detection = 0;
int half_hour = 1000 * 60 * 30;
float humidity;
float temperature;
String status;
String current_datetime;
StaticJsonDocument<200> docStatus;
StaticJsonDocument<200> docAlarm;
StaticJsonDocument<200> docTelegram;
StaticJsonDocument<200> docCoordinates;

// Update these with values suitable for your network.
const char* ssid = "PTVTELECOM_bQPS";
const char* password = "REHb3RSGTQCQ";
//const char* ssid = "WIN-LAOM7JEF5R6 9062";
//const char* password = "Lz0492&6";
const char* mqtt_server = "35.192.204.119";

String ID_PLACA;
String topic_PUB_telegram = "data/telegram/nicolo";
String topic_PUB_bigQuery = "data/google/nicolo";
String topic_PUB_coordinates = "data/coordinates/nicolo";
String topic_SUB_alarm = "cmd/alarm/nicolo"; // Subscription topic
String topic_SUB_status = "cmd/status/nicolo"; // Subscription topic

void conecta_wifi() {
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
      number_detection = 0;
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
    current_datetime = timeClient.getFormattedTime();
    docTelegram["temperature"] = temperature;
    docTelegram["humidity"] = humidity;
    docTelegram["alarm"] = status;
    docTelegram["detection"] = number_detection;
    docTelegram["time"] = current_datetime;
    
    String house_status;
    serializeJson(docTelegram, house_status);
    Serial.println();
    Serial.println("Topic   : " + topic_PUB_telegram);
    Serial.println("Payload : " + house_status);
    mqtt_client.publish(topic_PUB_telegram.c_str(), house_status.c_str());
    
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
  digitalWrite(PIN_RED_LED, HIGH);

  docCoordinates["longitude"] = -4.426812;
  docCoordinates["latitude"] = 36.713397;
  String msgCoordinates;
  serializeJson(docCoordinates, msgCoordinates);

  Serial.println();
  Serial.println("Topic   : " + topic_PUB_coordinates);
  Serial.println("Payload : " + msgCoordinates);
  
  mqtt_client.publish(topic_PUB_coordinates.c_str(), msgCoordinates.c_str());
  
  timeClient.setTimeOffset(utcOffsetInSeconds);
  timeClient.begin();
}

unsigned long last_message = 0;
unsigned long last_alarm_message = 0;
void loop() {
  if (!mqtt_client.connected()) conecta_mqtt();
  mqtt_client.loop();
  timeClient.update();
  unsigned long now = millis();

  bool sensorValue = digitalRead(PIN_MOTION_SENSOR);
  //Serial.print("Sensor Value: ");
  //Serial.println(sensorValue);

  if (alarm) {
    if (sensorValue) {
      tone(PIN_SPEAKER, 440);
      delay(1000);

      number_detection++;
      noTone(PIN_SPEAKER);
      delay(1000);   
    }
  }

  if (alarm && (number_detection > 0) && (now - last_alarm_message >= 20000)) {
    humidity = dht.getHumidity();
    temperature = dht.getTemperature();
    last_alarm_message = now;
    String current_datetime = timeClient.getFormattedTime();
    docAlarm["id"] = "id2";
    docAlarm["temperature"] = temperature;
    docAlarm["humidity"] = humidity;
    docAlarm["Alarm Status"] = sensorValue;
    docAlarm["Number Detection"] = number_detection;
    docAlarm["longitude"] = -4.426812;
    docAlarm["latitude"] = 36.713397;
    docAlarm["time"] = current_datetime;

    String msgAlarm;
    serializeJson(docAlarm, msgAlarm);
    Serial.println();
    Serial.println("Topic   : " + topic_PUB_bigQuery);
    Serial.println("Payload : " + msgAlarm);
    mqtt_client.publish(topic_PUB_bigQuery.c_str(), msgAlarm.c_str());
    
  }

  if (now - last_message >= half_hour) {
    humidity = dht.getHumidity();
    temperature = dht.getTemperature();
    last_message = now;
    String current_datetime = timeClient.getFormattedTime();
    docStatus["id"] = "id2";
    docStatus["temperature"] = temperature;
    docStatus["humidity"] = humidity;
    docStatus["Alarm Status"] = sensorValue;
    docStatus["Number Detection"] = number_detection;
    docStatus["longitude"] = -4.426812;
    docStatus["latitude"] = 36.713397;
    docStatus["time"] = current_datetime;

    String msgBigQuery;
    serializeJson(docStatus, msgBigQuery);
    Serial.println();
    Serial.println("Topic   : " + topic_PUB_bigQuery);
    Serial.println("Payload : " + msgBigQuery);
    mqtt_client.publish(topic_PUB_bigQuery.c_str(), msgBigQuery.c_str());
  }
}

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
NTPClient timeClient(ntpUDP, "time.google.com", utcOffsetInSeconds);

int PIN_MOTION_SENSOR = 4;
int PIN_SPEAKER = 12;
int PIN_RED_LED = 13;
int PIN_GREEN_LED = 15;
bool alarm = false;
int number_detection = 0;
int half_hour = 1000 * 60 * 30;
volatile float humidity;
volatile float temperature;
String status;
String current_datetime;
float latitude_home = 46.48689;
float longitude_home = 11.32225;
float limitTemperatureHigh = 200;
float limitTemperatureLow = -200;
float limitHumidityHigh = 200;
float limitHumidityLow = -200;


// Update these with values suitable for your network.
const char* ssid = "PTVTELECOM_bQPS";
const char* password = "REHb3RSGTQCQ";
//const char* ssid = "WIN-LAOM7JEF5R6 9062";
//const char* password = "Lz0492&6";
const char* mqtt_server = "35.192.204.119";

String ID_PLACA;
String topic_PUB_telegram = "data/telegram/Bolzano";
String topic_PUB_bigQuery = "data/google/Bolzano";
String topic_PUB_website = "data/website/Bolzano";
String topic_PUB_coordinates = "data/google/coordinates";
String topic_PUB_limit = "data/limit/Bolzano";
String topic_SUB_alarm = "cmd/alarm/Bolzano"; // Subscription topic
String topic_SUB_status = "cmd/status/Bolzano"; // Subscription topic
String topic_SUB_limit = "cmd/limit/Bolzano";

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

      mqtt_client.subscribe(topic_SUB_limit.c_str());
      Serial.println("Subscribed to topic: " + topic_SUB_limit);
    } else {
      Serial.println("ERROR:" + String(mqtt_client.state()) + " retrying in 5s");
      delay(5000);
    }
  }
}

String epochToDateTimeString(time_t epochTime) {
    struct tm *ptm = gmtime ((time_t *)&epochTime);
    String formattedDateTime;
    String day;
    String month;
    String year;
    String hourss;
    String minutess;
    String secondss;
    
    int monthDay = ptm->tm_mday;
    int currentMonth = ptm->tm_mon+1;
    int currentYear = ptm->tm_year+1900;

    int hours = ptm->tm_hour;
    int minutes = ptm->tm_min;
    int seconds = ptm->tm_sec;

    if(monthDay < 10){
      day = "0" + String(monthDay); 
    }else{
      day = String(monthDay); 
    }

    if(currentMonth < 10){
      month = "0" + String(currentMonth); 
    }else{
      month = String(currentMonth); 
    }

    if(hours < 10){
      hourss = "0" + String(hours); 
    }else{
      hourss = String(hours); 
    }

    if(minutes < 10){
      minutess = "0" + String(minutes); 
    }else{
      minutess = String(minutes); 
    }

    if(seconds < 10){
      secondss = "0" + String(seconds); 
    }else{
      secondss = String(seconds); 
    }
    
    formattedDateTime = String(currentYear) + "-" + month + "-" + day + " " + hourss + ":" + minutess + ":" + secondss + " UTC";

    return formattedDateTime;
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
      mqtt_client.publish(topic_PUB_website.c_str(), "1");
      Serial.println("Topic   : " + topic_PUB_website);
      Serial.println("Payload : 1");
    } else {
      Serial.println("Alarm is off!!");
      digitalWrite(PIN_GREEN_LED, LOW);
      digitalWrite(PIN_RED_LED, HIGH);
      alarm = false;
      mqtt_client.publish(topic_PUB_website.c_str(), "0");
      Serial.println("Topic   : " + topic_PUB_website);
      Serial.println("Payload : 0");
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
    StaticJsonDocument<200> docTelegram;
    
    current_datetime = epochToDateTimeString(timeClient.getEpochTime());
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

  if (String(topic) == topic_SUB_limit) {
    payload[length] = '\0';
    DynamicJsonDocument docLimit(256);
    //Deserialize the message to obtain all the data
    DeserializationError error = deserializeJson(docLimit, message);
  
    if (error) {
      Serial.print(("deserializeJson() failed: "));
      Serial.println(error.f_str());
      return;
    }

    limitTemperatureHigh = docLimit["limitTemperatureHigh"];
    limitTemperatureLow = docLimit["limitTemperatureLow"];
    limitHumidityHigh = docLimit["limitHumidityHigh"];
    limitHumidityLow = docLimit["limitHumidityLow"];

    Serial.println("max")
  }
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
  
  StaticJsonDocument<200> docCoordinates;
  docCoordinates["idHouse"] = "Bolzano";
  docCoordinates["longitude"] = longitude_home;
  docCoordinates["latitude"] = latitude_home;
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
unsigned long last_limit_message = 0;

void loop() {
  if (!mqtt_client.connected()) conecta_mqtt();
  mqtt_client.loop();
  timeClient.update();
  unsigned long now = millis();

  bool sensorValue = digitalRead(PIN_MOTION_SENSOR);
  
  if (alarm) {
    if (sensorValue) {
      tone(PIN_SPEAKER, 440);
      delay(1000);

      number_detection++;
      noTone(PIN_SPEAKER);
      delay(1000);   
    }
  }

  if (alarm && (number_detection > 0) && (now - last_alarm_message >= 10000)) {
    StaticJsonDocument<200> docAlarm;
    
    humidity = dht.getHumidity();
    temperature = dht.getTemperature();
    
    last_alarm_message = now;
    current_datetime = epochToDateTimeString(timeClient.getEpochTime());
    
    docAlarm["id"] = "id2";
    docAlarm["temperature"] = temperature;
    docAlarm["humidity"] = humidity;
    docAlarm["alarm_status"] = alarm;
    docAlarm["number_detection"] = number_detection;
    docAlarm["longitude"] = longitude_home;
    docAlarm["latitude"] = latitude_home;
    docAlarm["time"] = current_datetime;

    String msgAlarm;
    serializeJson(docAlarm, msgAlarm);
    Serial.println();
    Serial.println("Topic   : " + topic_PUB_bigQuery);
    Serial.println("Payload : " + msgAlarm);
    mqtt_client.publish(topic_PUB_bigQuery.c_str(), msgAlarm.c_str());
    
  }

  if (now - last_message >= 20000) {
    StaticJsonDocument<200> docStatus;
    
    humidity = dht.getHumidity();
    temperature = dht.getTemperature();
    last_message = now;
    current_datetime = epochToDateTimeString(timeClient.getEpochTime());
    //epochToDateTimeString(timeClient.getEpochTime());
    //Serial.println("current: " + current_datetime);
    docStatus["id"] = "id2";
    docStatus["temperature"] = temperature;
    docStatus["humidity"] = humidity;
    docStatus["alarm_status"] = alarm;
    docStatus["number_detection"] = number_detection;
    docStatus["longitude"] = longitude_home;
    docStatus["latitude"] = latitude_home;
    docStatus["time"] = current_datetime;

    String msgBigQuery;
    serializeJson(docStatus, msgBigQuery);
    Serial.println();
    Serial.println("Topic   : " + topic_PUB_bigQuery);
    Serial.println("Payload : " + msgBigQuery);
    mqtt_client.publish(topic_PUB_bigQuery.c_str(), msgBigQuery.c_str());
  }

  if (now - last_limit_message >= 10000){
    last_limit_message = now;
    humidity = dht.getHumidity();
    temperature = dht.getTemperature();

    if(temperature > limitTemperatureHigh || temperature < limitTemperatureLow || humidity > limitHumidityHigh || humidity < limitHumidityLow){
      StaticJsonDocument<200> docLimitMSG;
      current_datetime = epochToDateTimeString(timeClient.getEpochTime());
      
      if(temperature > limitTemperatureHigh){
        docLimitMSG["alarm_temperature"] = "too high!";
        docLimitMSG["temperature"] = temperature;
      } else if(temperature < limitTemperatureLow){
        docLimitMSG["alarm_temperature"] = "too low!";
        docLimitMSG["temperature"] = temperature;  
      } else if(humidity > limitHumidityHigh){
        docLimitMSG["alarm_humidity"] = "too high!";
        docLimitMSG["humidity"] = humidity;
      } else if(humidity < limitHumidityLow){
        docLimitMSG["alarm_humidity"] = "too low!";
        docLimitMSG["humidity"] = humidity;
      }

      docLimitMSG["time"] = current_datetime;
      
      String msgLimitWebsite;
      serializeJson(docLimitMSG, msgLimitWebsite);
      Serial.println();
      Serial.println("Topic   : " + topic_SUB_limit);
      Serial.println("Payload : " + msgLimitWebsite);
      mqtt_client.publish(topic_SUB_limit.c_str(), msgLimitWebsite.c_str()); 
    
    }
  }
  
}

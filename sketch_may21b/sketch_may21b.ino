#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include "DHTesp.h"
#include <time.h>

WiFiClient wClient;
PubSubClient mqtt_client(wClient);
DHTesp dht;

// Update these with values suitable for your network.
const char* ssid = "WIN-LAOM7JEF5R6 9062";
const char* password = "Lz0492&6";
const char* mqtt_server = "35.192.204.119";

String ID_PLACA;
String topic_PUB = "home1/data";

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
    } else {
      Serial.println("ERROR:" + String(mqtt_client.state()) + " retrying in 5s");
      delay(5000);
    }
  }
}

String getFormattedDate() {
  time_t now = time(nullptr);
  struct tm* p_tm = localtime(&now);
  char date_string[11]; // YYYY-MM-DD format
  snprintf(date_string, sizeof(date_string), "%04d-%02d-%02d", p_tm->tm_year + 1900, p_tm->tm_mon + 1, p_tm->tm_mday);
  return String(date_string);
}

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("Setup started...");
  ID_PLACA = "ESP_" + String(ESP.getChipId());
  conecta_wifi();
  mqtt_client.setServer(mqtt_server, 1883);
  mqtt_client.setBufferSize(512);
  conecta_mqtt();
  Serial.println("Device ID: " + ID_PLACA);
  Serial.println("Publication Topic: " + topic_PUB);
  Serial.println("Setup finished in " + String(millis()) + " ms");
  dht.setup(5, DHTesp::DHT11);

  // Set up NTP
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
}

unsigned long last_message = 0;

void loop() {
  if (!mqtt_client.connected()) conecta_mqtt();
  mqtt_client.loop();
  unsigned long now = millis();
  if (now - last_message >= 10000) {
    float humidity = dht.getHumidity();
    float temperature = dht.getTemperature();
    last_message = now;
    String current_date = getFormattedDate();
    String mensaje = "{\"id\":\"id1\", \"temperature\":" + String(temperature, 2) + ", \"humidity\":" + String(humidity, 2) +
                     ", \"motionDetection\":" + String(true ? "true" : "false") + ", \"longitude\":" + String(12.0, 6) + 
                     ", \"latitude\":" + String(50.0, 6) + ", \"time\":\"" + current_date + "\"}";
    Serial.println();
    Serial.println("Topic   : " + topic_PUB);
    Serial.println("Payload : " + mensaje);
    mqtt_client.publish(topic_PUB.c_str(), mensaje.c_str());
  }
}

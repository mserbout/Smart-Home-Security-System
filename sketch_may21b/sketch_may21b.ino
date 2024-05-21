#include <ESP8266WiFi.h>
#include "DHTesp.h"

// Replace with your network credentials
const char* ssid = "bra";
const char* password = "00000000";

DHTesp dht;

void setup() {
  // Start the serial communication to get information via serial monitor
  Serial.begin(115200);
  delay(10);

  // Start the WiFi connection
  Serial.println();
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  // Begin WiFi connection
  WiFi.begin(ssid, password);

  // Wait until the connection has been established
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  // Connection established
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());

  dht.setup(5, DHTesp::DHT11); // Connect DHT sensor to GPIO 5
}

unsigned long ultimo_mensaje=0;

void loop() {
  // Put your main code here, to run repeatedly

  unsigned long ahora = millis();

  if (ahora - ultimo_mensaje >= 3000) {
    float humidity = dht.getHumidity();
    float temperature = dht.getTemperature();
    ultimo_mensaje = ahora;
    String mensaje = "{\"temperatura\":" + String(temperature) + ", \"humedad\":" + String(humidity) + "}";
    Serial.println();
    Serial.println("Payload : "+ mensaje);
    
  }
}

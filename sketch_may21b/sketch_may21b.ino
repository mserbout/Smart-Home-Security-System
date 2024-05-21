#include <string>
#include <ESP8266WiFi.h>
#include "DHTesp.h"


WiFiClient wClient;
DHTesp dht;

// Update these with values suitable for your network.
const String ssid = "master1";
const String password = "mohamed11";

// cadenas para topics e ID
String ID_PLACA;


// GPIOs
int LED1 = 2;  
int LED2 = 16; 

//-----------------------------------------------------
void conecta_wifi() {
  Serial.println("Connecting to " + ssid);
 
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    digitalWrite(LED1,!digitalRead(LED1));
    delay(200);
    Serial.print(".");
  }
  digitalWrite(LED1,HIGH);
  Serial.println();
  Serial.println("WiFi connected, IP address: " + WiFi.localIP().toString());
}




void setup() {
  Serial.begin(115200);
  
  Serial.println();
  Serial.println("Empieza setup...");
  
  pinMode(LED1, OUTPUT);    // inicializa GPIO como salida
  pinMode(LED2, OUTPUT);    
  digitalWrite(LED1, LOW); 
  digitalWrite(LED2, HIGH); // apaga el led
  
  // crea topics usando id de la placa
  ID_PLACA="ESP_" + String( ESP.getChipId() );
  conecta_wifi();
  
  
  Serial.println("Identificador placa: "+ ID_PLACA);
  Serial.println("Termina setup en " +  String(millis()) + " ms");

  dht.setup(5, DHTesp::DHT11); // Connect DHT sensor to GPIO 5
}


unsigned long ultimo_mensaje=0;

void loop() {
  
  
  unsigned long ahora = millis();

  if (ahora - ultimo_mensaje >= 10000) {
    float humidity = dht.getHumidity();
    float temperature = dht.getTemperature();
    ultimo_mensaje = ahora;
    String mensaje = "{\"temperatura\":" + String(temperature) + ", \"humedad\":" + String(humidity) + "}";
    Serial.println();
    Serial.println("Payload : "+ mensaje);
    
    
    digitalWrite(LED2, LOW); // enciende el led al enviar mensaje
  }
}

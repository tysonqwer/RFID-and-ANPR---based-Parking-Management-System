#include <SPI.h>
#include <MFRC522.h>
#include <Adafruit_VL53L0X.h>
#include <Wire.h>
#include <Servo.h>

#define RST_PIN         9          
#define SS_PIN          10  
#define threshold 

MFRC522 mfrc522(SS_PIN, RST_PIN);  
Adafruit_VL53L0X lox = Adafruit_VL53L0X();
Servo myServo;


enum GateState { CLOSED, OPEN };
GateState gate = CLOSED;
bool active = false;

void setup() {
  Serial.begin(9600);		

  // RFID init
	SPI.begin();			
	mfrc522.PCD_Init();		
	Serial.println("RFID is ready to read ! ");

  //VL53L0X init
  Wire.begin()
  if(!lox.begin()){
    Serial.println("Failed to boot !")
    while(1);
  }
  Serial.println("VL53L0X is ready to read")

  // Servo init
  myServo.attach(9);  // Attach servo to pin D9

}

void loop() {
  // RFID READ AND SEND
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) return;
  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) uid += "0";  
    uid += String(rfid.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();
  while (uid.length() < 12) uid = "0" + uid;
  if (uid.length() > 12) uid = uid.substring(0, 12);
  Serial.print(uid);
  rfid.PICC_HaltA();
  delay(1000);  
  
  // RECEIVE INPUT FROM USER (UID MATCHES THE DATABASE)
  if(Serial.available() > 0){
    userInput = Serial.read();
    if(userInput == 'y'){
      // ACTIVATE LOGIC
      active = true;
      activate_logic();
    }
      
    }
  }
}

void activate_logic(){
  static unsigned long lastRead = millis();
  static unsigned long openTime = 0;
  static uint16_t distance = 9999;
  while(active){
    // UPDATE SENSOR EVERY 100MS
    if(millis() - lastRead >= 100){
      lastRead = millis();
      VL53L0X_RangingMeasurementData_t measure;
      lox.rangingTest(&measure, false);
      if(measure.RangeStatus != 4){
        distance = measure.RangeMilliMeter;
      }
    }
    // GATE LOGIC
    switch(gate){
      case CLOSED:
        if(distance < threshold){
          myServo.write(90);
          gate = OPEN;
          openTime = millis();
        }
        if(lastRead >= 60000){
          active = false;
        }
        break;

      case OPEN:
        if(distance >= threshold || (millis() - openTime >= 30000)){
          myServo.write(0);
          gate = CLOSED;
          active = false;
        }
        break;
    }
  }
}
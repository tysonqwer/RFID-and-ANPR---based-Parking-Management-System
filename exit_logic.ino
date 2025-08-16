#include <Wire.h>
#include <LCD_I2C.h>

#define SLOTS 3
int irPins[SLOTS] = {8, 9, 10};  // IR sensors for Slot 1 and Slot 2
bool slotStatus[SLOTS];      // 0 = empty, 1 = filled
LCD_I2C lcd(0x27, 16, 2); // address, columns, rows

void setup() {
  lcd.begin();
  lcd.backlight();

  for (int i = 0; i < SLOTS; i++) {
    pinMode(irPins[i], INPUT);
    slotStatus[i] = false;
  };
  lcd.setCursor(0, 0);
  lcd.print("Parking System");
  delay(1500);

}

void loop() {
  // Read each IR sensor
  int count = 0;
  for (int i = 0; i < SLOTS; i++) {
    int sensorValue = digitalRead(irPins[i]);
    slotStatus[i] = (sensorValue == LOW); // LOW means filled
  }

  // Display both slots on the LCD
  for(int i = 0; i < SLOTS; i++){
    if(slotStatus[i]) count++; 
  }
  if(count == SLOTS){
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("FULL");
  }
  else{
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Available Slots:");
    lcd.setCursor(0, 1);
    lcd.print(SLOTS - count);
  }
  delay(200); // small delay for stability
}
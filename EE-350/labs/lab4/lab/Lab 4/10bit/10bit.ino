/*
 * REAL HARDWARE SAR ADC (10-BIT VERSION)
 * --------------------------------------
 * HARDWARE:
 * - Pin 3 (DAC_PIN)  -> To RC Filter Input (PWM)
 * - Pin 2 (COMP_PIN) -> To TL082 Output (Pin 1)
 * - TL082 Pin 3 (+)  -> Vin (Potentiometer)
 * - TL082 Pin 2 (-)  -> Vdac (Output of RC Filter)
 * * USAGE:
 * - Send 'b': Begin conversion (Starts at 2.5V)
 * - Send 'n': Next step
 */

const int COMP_PIN = 2;
const int DAC_PIN = 3;

// --- Global Variables ---
int digitalValue = 0;
int currentBit = 9; // MSB for 10-bit is Bit 9
bool conversionInProgress = false;

// PWM Timing
const int pwm_step_us = 10; 
const int MAX_VAL = 1024; // 2^10

// Helper: Print 10-Bit Binary
void printBinary(int value) {
  for (int i = 9; i >= 0; i--) {
    Serial.print((value >> i) & 1);
  }
}

// --- CONVERSION STEP ---
void performConversionStep() {
  if (!conversionInProgress) return;

  // 1. KARŞILAŞTIRMA VE KARAR AŞAMASI (O anki currentBit için)
  int compOut = digitalRead(COMP_PIN);
  
  if (compOut == LOW) { 
    digitalValue &= ~(1 << currentBit); // Bit reddedildi (Clear)
  }

  // 2. BİR SONRAKİ BİT İÇİN HAZIRLIK
  currentBit--; 

  if (currentBit < 0) {
    // --- FINISHED ---
    conversionInProgress = false;
    float finalVoltage = digitalValue * (5.0 / (float)MAX_VAL);
    Serial.println("----------------------------------------");
    Serial.println("FINAL RESULT");
    Serial.print("Reg: "); printBinary(digitalValue);
    Serial.print(" | Volt: "); Serial.print(finalVoltage, 3); Serial.println(" V");
    Serial.println("----------------------------------------\n");
  } else {
    // --- CONTINUE ---
    digitalValue |= (1 << currentBit); // Bir sonraki biti test için 1 yap
    
    // 3. ANLIK PWM VOLTAJINI YAZDIR (Multimetredeki değer)
    float currentPwmVoltage = digitalValue * (5.0 / (float)MAX_VAL);
    Serial.print("Bit ");
    Serial.print(currentBit);
    Serial.print(" | Reg: ");
    printBinary(digitalValue);
    Serial.print(" | PWM Voltaj: ");
    Serial.print(currentPwmVoltage, 3);
    Serial.println(" V");
  }
}

void setup() {
  Serial.begin(9600);
  pinMode(COMP_PIN, INPUT);
  pinMode(DAC_PIN, OUTPUT);
  digitalWrite(DAC_PIN, LOW);
  
  Serial.println("System Ready (10-Bit). Send 'b' to start.");
}

void loop() {
  // 1. Software PWM Generation (Background Task)
  int high_time = digitalValue * pwm_step_us;
  int low_time = (MAX_VAL - digitalValue) * pwm_step_us;
  
  if (digitalValue > 0) {
    digitalWrite(DAC_PIN, HIGH);
    delayMicroseconds(high_time);
  }
  if (digitalValue < MAX_VAL) {
    digitalWrite(DAC_PIN, LOW);
    delayMicroseconds(low_time);
  }

  // 2. Serial Control
  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == 'b') {
      conversionInProgress = true;
      currentBit = 9;
      digitalValue = (1 << currentBit); // Start with MSB (512)
      
      Serial.println("\n--- STARTING CONVERSION ---");
      
      // İlk adımın voltajını yazdır
      float currentPwmVoltage = digitalValue * (5.0 / (float)MAX_VAL);
      Serial.print("Bit 9 | Reg: ");
      printBinary(digitalValue);
      Serial.print(" | PWM Voltaj: ");
      Serial.print(currentPwmVoltage, 3);
      Serial.println(" V");
    } 
    else if (cmd == 'n') {
      performConversionStep();
    }
    // Flush buffer
    while(Serial.available()) Serial.read();
  }
}
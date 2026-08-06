
#define __DELAY_ROUND_CLOSEST__ 
#include <util/delay.h>
#include "pcjr_type.h"

// Hardware Pin Mappings (Mega Pin 5 = Port E, Bit 3)
#define TX_PIN_MASK       (1 << 3)

// Precise Timing Specifications (in microseconds)
#define BURST_DURATION    62.5
#define LOGIC_1_SILENCE   377.5
#define LOGIC_0_SILENCE_1 220.0
#define LOGIC_0_SILENCE_2 157.5
#define START_BIT_SILENCE 310

#define TIMER_40KHZ_MATCH 24

const int outputPin = 5;
const int triggerPin = 11;

void setup() {
  // Initialize Serial safely inside the official setup block
  Serial.begin(600); // Adjusted standard rate (or change to 600 if required)
  
	pinMode(triggerPin, OUTPUT);
  pinMode(outputPin, OUTPUT);
  PORTE |= TX_PIN_MASK;      // Force initial line to idle HIGH

  // Clear Timer 3 control registers to wipe default configurations
  TCCR3A = 0;
  TCCR3B = 0;
  TCNT3  = 0;
  OCR3A  = TIMER_40KHZ_MATCH;

  // Put Timer 3 into CTC Mode, but DO NOT start the clock selection yet
  TCCR3B |= (1 << WGM32);
}

// Connects the running timer to Pin 5 AND turns on the prescaler clock
void inline mark() {
  TCCR3A |= (1 << COM3A0);   // Route Timer 3 to automatically toggle Pin 5
  TCCR3B |= (1 << CS31);     // Turn on clock prescaler 8 to start 40kHz pulses
}

// Disconnects the timer completely, stops the clock, and resets pin state
void inline space() {
  TCCR3B &= ~(1 << CS31);    // Shut down the clock completely
  TCCR3A &= ~(1 << COM3A0);  // Unlink timer from physical silicon pin
  TCNT3 = 0;                 // Clear counter to prevent phase lag on next mark
  PORTE |= TX_PIN_MASK;      // Directly snap the pin back to absolute DC HIGH
}

void inline one() {
	mark(); _delay_us(BURST_DURATION);
	space(); _delay_us(LOGIC_1_SILENCE);
}

void inline zero() {
	space(); _delay_us(LOGIC_0_SILENCE_1);
	mark();  _delay_us(BURST_DURATION);
	space(); _delay_us(LOGIC_0_SILENCE_2);
}

void inline start() {
  mark();  _delay_us(BURST_DURATION);
	space(); _delay_us(START_BIT_SILENCE);
}

void manchester(uint8_t data) {
	PORTE |= 0x0;      // Directly snap the pin back to absolute DC HIGH
  noInterrupts(); 

	start();

	int parity = 0;
	
  for (uint8_t i = 0; i < 8; i++) {
    bool bit = (data >> i) & 0x01;

    if (bit == 1) { parity+=1; one(); }
    else { zero(); }
  }

	if (parity % 2 == 0){ one(); }
	else { zero(); }

	PORTE |= 0x0;
	_delay_us(4840);
  interrupts(); 
}

void loop() {
	while (Serial.available()) { 
		uint8_t code = Serial.read();
		manchester(code);
	}
}

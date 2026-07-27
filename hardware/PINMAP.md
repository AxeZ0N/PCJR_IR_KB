# Pin Mapping – Elegoo Mega2560

| Function | Arduino Mega Pin | ATmega2560 Port | Register Bit | Notes |
|----------|------------------|-----------------|--------------|-------|
| 40 kHz Output (OC3A) | 5 | PORTE | 3 | Timer 3 CTC mode, toggle on compare match |
| Trigger (optional) | 11 | PORTB | 5 | Used for scope triggering |

## Register Names
The Elegoo Mega2560 variant uses the standard AVR register names for the ATmega2560:

```c
TCCR3A  // Timer 3 Control Register A
TCCR3B  // Timer 3 Control Register B
OCR3A   // Output Compare Register 3A
TCNT3   // Timer 3 Counter

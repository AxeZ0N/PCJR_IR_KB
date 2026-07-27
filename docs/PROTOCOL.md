# PCjr Infrared Keyboard Protocol

## Physical Layer
- **Carrier:** 40 kHz, 50% duty cycle (12 µs high, 13 µs low)  
- **Modulation:** Active‑low – idle line is HIGH, carrier burst drives line LOW  
- **Burst duration:** 62.5 µs (exactly 2.5 carrier cycles)

## Bit Encoding
Each bit cell is **440 µs** divided into two 220 µs half‑bits (biphase Manchester):

- **Logic 1:** Carrier ON in first half‑bit, OFF in second half‑bit  
  → 62.5 µs burst + 157.5 µs silence = 220 µs, then 220 µs silence  
- **Logic 0:** Silence in first half‑bit, carrier ON in second half‑bit  
  → 220 µs silence, then 62.5 µs burst + 157.5 µs silence

## Frame Structure
1. **Start bit** – carrier burst (62.5 µs) + 310 µs silence  
2. **8 data bits** – scan code, LSB first  
3. **Odd parity bit** – parity over data bits (1 = odd)  
4. **Stop bit** – a full logic 1 (carrier in first half, silence in second)  
5. **Idle tail** – 4840 µs silence (11 extra stop bits)

Total frame length: 372.5 µs (start) + 11×440 µs = 5.212 ms

## Scan Codes
PC/XT Set 1 scan codes (subset):

| Key | Code | Key | Code |
|-----|------|-----|------|
| a   | 0x1E | 0   | 0x0B |
| b   | 0x30 | 1   | 0x02 |
| ... | ...  | ... | ...  |
| h   | 0x23 | space | 0x39 |
| Enter | 0x1C |     |      |

Full table in `docs/SCANCODES.md`.

## Break Codes
Key release is signalled by sending the make code with the high bit set (make | 0x80).  
Example: `'h'` make = 0x23, break = 0xA3.

## Receiver Sampling
The PCjr's 8088 NMI routine samples the keyboard data line:
- Trigger: trailing (rising) edge of start burst  
- Wait 310 µs, then sample every 220 µs (center of each half‑bit)  
- Each half‑bit is sampled 5 times, majority vote used

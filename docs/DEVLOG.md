# Reverse Engineering Log – PCjr IR Protocol

## 1. Initial State
- Community code (Arduino `jblang` library) produced no response.  
- LLM‑generated pulse‑distance code produced error beeps, but no keystrokes.  
- IBM PCjr Technical Reference (1983) describes biphase Manchester, but is it correct?

## 2. Forensic Foundation
**Lemma 0:** A steady‑on IR LED causes rapid error beeps → physical link works.  
**Experimental approach:** Design tests that isolate one variable, verify on scope, observe beep/silence.

## 3. Isolating the Start Condition
- Single 66 µs pulse + long idle → silence.  
- Start + 0‑2 data bits (pulse‑distance) → silence.  
- Start + 3 data bits → **beep!**  
  → Receiver requires at least 3 bits before committing to an error check.

## 4. Synchronisation Window
Swept start‑gap from 100 µs to 2000 µs with 3‑bit frames.  
- Gaps 190–255 µs: silence (possibly valid sync or no sync).  
- Gap ~265 µs: rapid beeps (misaligned sampling).  
- Gap >275 µs: silence (no trigger).  

Tested with intentional parity error at 200 µs – still silence → could not distinguish perfect decode from no sync.

## 5. Encoding Wars: Pulse‑distance vs. Manchester
- Full pulse‑distance frame (correct parity) → **beep**.  
- Same frame with flipped parity → **beep**.  
  → Error is NOT parity; the receiver rejects the pulse‑distance encoding as a phase error.  
- Implemented exact Manchester per IBM manual (62.5 µs bursts, 220 µs half‑bits).  
- First test: **`h` appears on screen, no beep!**  
  → The manual was correct all along.

## 6. Hardware Pitfalls
- Elegoo Mega2560 uses different timer register names than Arduino Mega.  
- Initial code (LLM‑generated) assumed Arduino register map → silent failure.  
- Resolved by cross‑referencing ATmega2560 datasheet and board variant files.

## 7. Conclusion
The original IBM specification is accurate. Community lore (pulse‑distance) is incorrect.  
The project succeeded through rigorous variable isolation, scope‑verified measurements, and refusal to accept "beep = working".

## Key Takeaways
- Trust the original spec (but verify).  
- A beep only proves the receiver saw *something*, not that it decoded correctly.  
- Microsecond precision requires hardware timers, not bit‑banging.  
- Clone boards are not always register‑compatible – always check the datasheet.

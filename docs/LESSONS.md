# Lessons Learned – PCjr IR Emulator

## 1. Clone Boards Are Not Drop‑in Replacements
The Elegoo Mega2560 and Arduino Mega2560 share the ATmega2560 chip, but their compiler‑defined register names differ.  
**Always** verify the timer/pin mapping against the datasheet and the board’s variant header file before writing bare‑metal code.

## 2. A Beep Is Not a Valid Signal
Error beeps only prove the receiver detected an edge and attempted a decode. They do NOT indicate correct bit encoding or frame content.  
Only a character on the screen (or a scope trace of the receiver’s output) counts as success.

## 3. The Original Spec Was Right
The IBM PCjr Technical Reference (1983) perfectly describes the biphase Manchester protocol.  
Community code that “worked” actually produced error beeps, misleading developers.  
Lesson: Distrust folklore; verify with controlled experiments.

## 4. Oscilloscope at the Transducer, Not the GPIO
Verifying waveforms at the LED driver (or with a photodiode) reveals distortions the GPIO pin trace hides.  
A perfect electrical signal doesn’t guarantee correct optical output.

## 5. Forensic Methodology Wins
By proving each lemma (physical link, minimum bits, sync window, encoding) before advancing, I avoided weeks of guesswork.  
This disciplined approach also made the work explainable and defensible.

## 6. Hardware Timers Are Mandatory for µs Precision
Software delay loops drift and jitter; only a hardware timer (CTC mode) can produce rock‑solid 62.5 µs bursts.  
This is especially critical when the receiver uses a fixed sampling clock locked to the carrier.

## 7. Parity and Phase Errors Sound the Same (on this hardware)
Despite the manual describing distinct beeps, I could not audibly differentiate them.  
Do not assume an error indicator is more granular than it actually is.

## 8. Separate Systems, Then Integrate
The transmitter, PCjr, oscilloscope, and remote audio/video were each treated as independent projects.  
Integration only after each worked standalone. This kept complexity manageable.

#include <RCSwitch.h>
RCSwitch myTX = RCSwitch();

unsigned long ON_CODES[5] = {
  0x2F35A , // 1 UNKNOWN
  0x2F35AA, // 2 PCJrduino
  0x2F35A , // 3 UNKNOWN
  0x2F35A , // 4 UNKNOWN
  0x2F35AB, // 5 Klipptop (3D Printer) 
};

unsigned long OFF_CODES[5] = {
  0x2F35A , // 1 UNKNOWN
  0x2F35A2, // 2 PCJrduino
  0x2F35A , // 3 UNKNOWN
  0x2F35A , // 4 UNKNOWN
  0x2F35A3, // 5 Klipptop (3D Printer)
};

#define PROTO 1
#define PIN 10
#define PULSELENGTH 149
#define REPEATS 15

void setup_tx(int tx_pin = PIN, int tx_protocol = PROTO,
              int tx_pulselength = PULSELENGTH,
              int tx_repeats = REPEATS) {
  myTX.enableTransmit(PIN); // Transmitter is connected to Arduino Pin #10
  myTX.setProtocol(tx_protocol); // Optional set protocol (default is 1, \)
  myTX.setPulseLength(tx_pulselength); // Optional set pulse length.
  myTX.setRepeatTransmit(tx_repeats);// Optional set number of transmission repetitions.

}

void setup_rx(RCSwitch rx_switch, int rx_interrupt = 0) {
  // Receiver on interrupt 0 => that is pin #2)
  rx_switch.enableReceive(rx_interrupt);
}

void parseInput(int ID, int STATE) {
  if (ID < 0 or ID > sizeof(ON_CODES)) {
    //Serial.println("Not in array");
    return;
  }

  unsigned long data;
  if (STATE == 1) {
    data = ON_CODES[ID - 1];
  }
  else if (STATE == 0) {
    data = OFF_CODES[ID - 1];
  }

  for (unsigned long i = 0; i < 1; i++) {
    myTX.send(data, 24);
    //Serial.print(ID); Serial.print(" "); Serial.println(data, HEX);
  }


}
void setup_PowerPCJr() {
	return
  setup_tx();

	// Flush buffer and wait for magic byte
	while (Serial.available()) {Serial.read();}
	parseInput(2, 0);
	while (Serial.parseInt() != 1) {
		Serial.println("Press 1 to cont.");
	};

	// Mode 0 is PowerPCJr, Mode 1 is ir_bridge
	Serial.println("Choose mode: 0 = Outlet On/Off. 1 = PCJr IR Bridge");
	while (not Serial.available()) { };
	int mode = Serial.parseInt();
	Serial.print("Mode chosen: ");
	Serial.println(mode);

	if (mode == 0) {
		// In mode 0, the next int sets the state of the outlet 1/0
		// Then go in to normal mode
		Serial.println("Choose outlet state: 0 = Off, 1 = On");
		while (not Serial.available()) { };
		int state = Serial.parseInt();
		Serial.print("State chosen: ");
		Serial.println(state);
		parseInput(2, state);
	}
	// In mode 1, we just fall through to normal execution
}

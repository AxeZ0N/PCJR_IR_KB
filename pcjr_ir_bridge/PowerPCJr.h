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

void setup_tx(int tx_pin = 10, int tx_protocol = 1,
              int tx_pulselength = 149,
              int tx_repeats = 15) {
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
    Serial.println("Not in array");
    return;
  }

  unsigned long data;
  if (STATE) {
    data = ON_CODES[ID - 1];
  }
  else {
    data = OFF_CODES[ID - 1];
  }

  for (unsigned long i = 0; i < 1; i++) {
    myTX.send(data, 24);
    Serial.print(ID); Serial.print(" "); Serial.println(data, HEX);
  }


}
void setup_PowerPCJr() {
    
  setup_tx();
  // setup_rx();
  
  Serial.println("Mode 0: PowerPCJr\nMode 1: IR Bridge");
  
  while (not Serial.available()) { };
  if (Serial.parseInt() == 0) { 
    Serial.println("Enter desired state 0/1:");
    while (not Serial.available()) { };
    parseInput(5, Serial.parseInt());
  }

  // setup_rx();
}


void loop() {

  Serial.println("Enter data: <outlet #> <state>");
  while (not Serial.available()) { };
  int ID = Serial.parseInt();
  int STATE = Serial.parseInt();
  parseInput(ID, STATE);

}

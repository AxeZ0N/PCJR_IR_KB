socat -v -x -u PTY,link=/tmp/virtual_arduino,raw,echo=0 file:/dev/ttyACM0,b600,raw,echo=0

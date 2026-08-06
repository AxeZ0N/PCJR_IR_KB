stty -F /dev/ttyACM0 600 raw -clocal -hupcl -echo   # Configure the port settings
echo "$1" > /dev/ttyACM0

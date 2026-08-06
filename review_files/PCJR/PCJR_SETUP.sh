#!/usr/bin/bash

install() {
	echo "Basic updating"
	sudo apt update -y && sudo apt upgrade -y

	echo "Installing helpers"
	sudo apt install -y vim git avrdude
	git clone https://github.com/jblang/pcjr_type

	echo "Installing arduino-cli"
	curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
	curl -fsSL https://raw.githubusercontent.com/AxeZ0N/vimrc/refs/heads/main/.vimrc > ~/.vimrc
	sudo chmod +x bin/arduino-cli
	sudo mv bin/arduino-cli /usr/local/bin
	rmdir bin
}

compile_and_upload() {
	echo "Compiling"
	sudo arduino-cli compile --fqbn arduino:avr:mega pcjr_type/ --build-path ./pcjr_type/build

	echo "Uploading"
	avrdude -v -p atmega2560 -c wiring -P /dev/ttyACM0 -b 115200 -D -U flash:w:pcjr_type/build/pcjr_type.ino.hex
}

sniff() {
	realpath="/dev/ttyACM0"
	fakepath="/tmp/virtual_arduino"
	echo "Sniffing $realpath -> $fakepath:"
	socat -v -x -u PTY,link="$realpath",raw,echo=0 "file:$fakepath",b600,raw,echo=0
}

stream() {
	echo "Run this on watching pc:"
	echo "ffplay udp://@:5000 -fflags nobuffer -flags low_delay -framedrop -loglevel quiet"
	rpicam-vid -t 0 -n --inline -o udp://192.168.4.36:5000 --verbose=0
}

configure() {
	echo "Configure arduino-cli"
	arduino-cli config init
	arduino-cli core update-index
	arduino-cli core install arduino:avr
}

all() {
	install
	configure
	compile_and_upload
}

use_component() {
	case $1 in
		"all")
			all
			;;
		"install")
			install
			;;
		"configure")
			;;
		"cu" | "compile_and_upload" | "compile" | "upload")
			compile_and_upload
			;;
		"sniff")
			sniff
			;;
	esac
}

if [[ $# > 0 ]] then
	echo "Using $1"
	use_component $1
	exit
else
	echo "Using all"
	all
fi

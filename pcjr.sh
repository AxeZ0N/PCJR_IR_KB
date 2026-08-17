#!/usr/bin/env bash
# pcjr.sh – Unified PCjr toolkit control
# Usage: ./pcjr.sh {setup|configure|compile|upload|cu|stream|server-setup|server-start|driver|help}
set -euo pipefail

# Determine the real user (before any sudo)
if [ -n "${SUDO_USER:-}" ]; then
    REAL_USER="$SUDO_USER"
else
    REAL_USER="$USER"
fi

# Work from the script's directory so relative paths are safe
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ----------------------------------------------------------------------
# Default configuration (override by creating pcjr.conf)
# ----------------------------------------------------------------------
SERIAL_DEVICE="/dev/ttyACM0"
SERIAL_BAUD=600
FQBN="arduino:avr:mega"
BUILD_DIR="./pcjr_ir_bridge/build"
STREAM_IP="192.168.4.34"
STREAM_PORT="8554"
STREAM_PATH="/cam"
PYTHON_DRIVER="./pcjr_control.py"
MEDIAMTX_CONFIG="./mediamtx.yml"
MEDIAMTX_INSTALL_DIR="/usr/local/bin"
MEDIAMTX_CONFIG_DEST="/etc/mediamtx.yml"
MEDIAMTX_SERVICE_NAME="mediamtx"

CONFIG_FILE="./pcjr.conf"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"   # overrides above defaults
fi

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
check_deps() {
    local missing=()
    for cmd in "$@"; do
        command -v "$cmd" &>/dev/null || missing+=("$cmd")
    done
    if [ ${#missing[@]} -gt 0 ]; then
        echo "Missing dependencies: ${missing[*]}" >&2
        echo "Run './pcjr.sh setup' first." >&2
        exit 1
    fi
}

# Detect architecture for MediaMTX download
get_arch() {
    local arch
    arch=$(uname -m)
    case "$arch" in
        x86_64)   echo "amd64" ;;
        aarch64)  echo "arm64v8" ;;
        armv6l)   echo "armv6" ;;
        armv7l)   echo "armv7" ;;
        *)        echo "unsupported ($arch)" >&2; exit 1 ;;
    esac
}

# ----------------------------------------------------------------------
# Commands
# ----------------------------------------------------------------------
setup() {
    echo "=== System setup ==="
    sudo apt update -y && sudo apt upgrade -y
    sudo apt install -y git avrdude socat python3-pip curl

    # arduino-cli
    if ! command -v arduino-cli &>/dev/null; then
        echo "Installing arduino-cli..."
        curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
        sudo mv bin/arduino-cli /usr/local/bin
        rmdir bin 2>/dev/null || true
    fi

    # Python driver dependencies
    if [ -f "$PYTHON_DRIVER" ]; then
        pip3 install --user pyserial
    fi

    echo "Done. Next: './pcjr.sh configure' then './pcjr.sh cu'"
}

configure() {
    check_deps arduino-cli
    echo "=== Configuring arduino-cli ==="
    arduino-cli config init
    arduino-cli core update-index
    arduino-cli core install "$FQBN"
}

compile() {
    check_deps arduino-cli
    echo "Compiling..."
    arduino-cli compile --fqbn "$FQBN" pcjr_ir_bridge/ --build-path "$BUILD_DIR"
		hupcl
}

upload() {
    check_deps avrdude
    echo "Uploading..."
    avrdude -v -p atmega2560 -c wiring -P "$SERIAL_DEVICE" -b 115200 -D \
        -U "flash:w:${BUILD_DIR}/pcjr_ir_bridge.ino.hex"
}

hupcl() {
		echo "$SERIAL_DEVICE hupcl now: ON"
		sudo stty -F $SERIAL_DEVICE hupcl
}

debug() {
    echo "Opening debug terminal"
		echo "Exit with <C-A> + K, Y"
		sleep 2
		hupcl
		screen $SERIAL_DEVICE $SERIAL_BAUD
}


compile_and_upload() {
    compile
    upload
}

stream() {
    check_deps mpv
    local rtsp_url="rtsp://${STREAM_IP}:${STREAM_PORT}${STREAM_PATH}"
    echo "Viewing RTSP stream at $rtsp_url"
    mpv \
        --profile=low-latency \
				--no-cache \
        --demuxer-lavf-o=rtsp_transport=tcp \
				--vd-lavc-threads=1 \
				--framedrop=vo \
				--speed=1.01 \
        "$rtsp_url" 
}

connect() {
	# pcjrduino IP
	ssh -t 192.168.4.34 "/home/k/PCJR_IR_KB/pcjr.sh driver" "$@"
}

# ----------------------------------------------------------------------
# MediaMTX server setup and control
# ----------------------------------------------------------------------
server-setup() {
    check_deps curl
    local arch
    arch=$(get_arch)
    # Update this to the latest release if needed
    local version="v1.20.0"
    local binary_url="https://github.com/bluenviron/mediamtx/releases/download/${version}/mediamtx_${version}_linux_${arch}.tar.gz"
    local tmpdir=$(mktemp -d)

    echo "=== Installing MediaMTX (stream server) ==="

    echo "Downloading MediaMTX $version for $arch..."
    curl -L "$binary_url" | tar xz -C "$tmpdir"

    sudo mv "$tmpdir/mediamtx" "$MEDIAMTX_INSTALL_DIR/mediamtx"
    sudo chmod +x "$MEDIAMTX_INSTALL_DIR/mediamtx"

    if [ -f "$MEDIAMTX_CONFIG" ]; then
        sudo cp "$MEDIAMTX_CONFIG" "$MEDIAMTX_CONFIG_DEST"
        echo "Config file installed to $MEDIAMTX_CONFIG_DEST"
    else
        echo "Warning: $MEDIAMTX_CONFIG not found – using default config"
    fi

    if command -v systemctl &>/dev/null; then
        echo "Creating systemd service for user '$REAL_USER'..."
        sudo tee /etc/systemd/system/${MEDIAMTX_SERVICE_NAME}.service >/dev/null <<EOF
[Unit]
Description=MediaMTX streaming server
After=network.target

[Service]
ExecStart=$MEDIAMTX_INSTALL_DIR/mediamtx $MEDIAMTX_CONFIG_DEST
Restart=on-failure
User=$REAL_USER

[Install]
WantedBy=multi-user.target
EOF
        sudo systemctl daemon-reload
        sudo systemctl enable "$MEDIAMTX_SERVICE_NAME"
        echo "Service enabled. Start with: sudo systemctl start $MEDIAMTX_SERVICE_NAME"
        echo "Or use './pcjr.sh server-start'"
    else
        echo "No systemd detected; start manually with './pcjr.sh server-start'"
    fi

    sudo systemctl daemon-reload
    sudo systemctl enable "$MEDIAMTX_SERVICE_NAME"
    echo "MediaMTX service enabled. Start with: sudo systemctl start $MEDIAMTX_SERVICE_NAME"
    echo "Or use './pcjr.sh server-start'"

    rm -rf "$tmpdir"
}

server-start() {
    if command -v systemctl &>/dev/null && systemctl is-enabled "$MEDIAMTX_SERVICE_NAME" &>/dev/null; then
        if systemctl is-active --quiet "$MEDIAMTX_SERVICE_NAME"; then
            echo "MediaMTX is already running."
        else
            sudo systemctl start "$MEDIAMTX_SERVICE_NAME"
            echo "Started MediaMTX service."
        fi
    else
        echo "Starting MediaMTX directly (Ctrl+C to stop)..."
        "$MEDIAMTX_INSTALL_DIR/mediamtx" "$MEDIAMTX_CONFIG_DEST"
    fi
}

driver() {
    if [ ! -f "$PYTHON_DRIVER" ]; then
        echo "Python driver not found: $PYTHON_DRIVER"
        exit 1
    fi
    python3 "$PYTHON_DRIVER" "$@"
}

help_msg() {
    cat <<EOF
PCJR Toolkit – Unified control script

Usage: ./pcjr.sh <command> [args]

Commands:
  setup               Install system packages & arduino-cli (run once)
  configure           Configure arduino-cli cores
  compile             Compile the Arduino sketch
  upload              Upload compiled sketch to the board
  cu                  Compile + upload
  stream              Open mpv to view the RTSP camera stream
  server-setup        Install MediaMTX and configure the camera server
  server-start        Start the MediaMTX server (systemd or foreground)
  driver [args...]    Run the Python interactive keyboard driver
	connect							SSH into pcjrduino in driver mode
  help                Show this message

All parameters are configurable in pcjr.conf.
EOF
}

# ----------------------------------------------------------------------
# Dispatcher
# ----------------------------------------------------------------------
if [ $# -eq 0 ]; then
    help_msg
    exit 1
fi

case "$1" in
    setup)          setup ;;
    configure)      configure ;;
    compile)        compile ;;
    upload)         upload ;;
    cu)             compile_and_upload ;;
    stream)         stream ;;
    server-setup)   server-setup ;;
    server-start)   server-start ;;
		hupcl)					hupcl;;
		debug)					debug;;
    driver)         shift; driver "$@" ;;
    connect)        shift; connect "$@" ;;
    help|--help|-h) help_msg ;;
    *)              echo "Unknown command: $1" >&2; help_msg; exit 1 ;;
esac

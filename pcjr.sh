#!/usr/bin/env bash
# pcjr.sh – Unified PCjr toolkit control
# Usage: ./pcjr.sh {setup|configure|compile|upload|cu|sniff|stream|server-setup|server-start|echo|driver|help}
set -euo pipefail

# Work from the script's directory so relative paths are safe
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ----------------------------------------------------------------------
# Default configuration (override by creating pcjr.conf)
# ----------------------------------------------------------------------
SERIAL_DEVICE="/dev/ttyACM0"
SERIAL_BAUD=600
FQBN="arduino:avr:mega"
BUILD_DIR="./pcjr_type/build"
STREAM_IP="192.168.4.34"
STREAM_PORT="8554"
STREAM_PATH="/cam"
SNIFF_FAKE_DEVICE="/tmp/virtual_arduino"
PYTHON_DRIVER="./pcjrduino_tty.py"
# MediaMTX settings
MEDIAMTX_CONFIG="./mediamtx.yml"          # source config in repo
MEDIAMTX_INSTALL_DIR="/usr/local/bin"     # where to put the binary
MEDIAMTX_SERVICE_NAME="mediamtx"          # systemd service name

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

# Detect architecture (used for MediaMTX binary download)
get_arch() {
    local arch
    arch=$(uname -m)
    case "$arch" in
        x86_64)  echo "amd64" ;;
        aarch64) echo "arm64" ;;
        armv7l)  echo "armv7" ;;
        *)       echo "unsupported ($arch)" >&2; exit 1 ;;
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
    arduino-cli compile --fqbn "$FQBN" pcjr_type/ --build-path "$BUILD_DIR"
}

upload() {
    check_deps avrdude
    echo "Uploading..."
    avrdude -v -p atmega2560 -c wiring -P "$SERIAL_DEVICE" -b 115200 -D \
        -U "flash:w:${BUILD_DIR}/pcjr_type.ino.hex"
}

compile_and_upload() {
    compile
    upload
}

sniff() {
    check_deps socat
    echo "Sniffing $SERIAL_DEVICE → $SNIFF_FAKE_DEVICE  (Ctrl+C to stop)"
    socat -v -x -u "PTY,link=${SNIFF_FAKE_DEVICE},raw,echo=0" \
        "file:${SERIAL_DEVICE},b${SERIAL_BAUD},raw,echo=0"
}

stream() {
    check_deps mpv
    local rtsp_url="rtsp://${STREAM_IP}:${STREAM_PORT}${STREAM_PATH}"
    echo "Viewing RTSP stream at $rtsp_url"
    mpv \
        --profile=low-latency \
        --cache=yes \
        --demuxer-lavf-o=rtsp_transport=tcp \
        "$rtsp_url"
}

# ----------------------------------------------------------------------
# MediaMTX server setup and control (for the Raspberry Pi / camera host)
# ----------------------------------------------------------------------
server-setup() {
    check_deps curl
    local arch
    arch=$(get_arch)
    local version="v1.10.0"          # update to latest stable if needed
    local binary_url="https://github.com/bluenviron/mediamtx/releases/download/${version}/mediamtx_${version}_linux_${arch}.tar.gz"
    local tmpdir=$(mktemp -d)

    echo "=== Installing MediaMTX (stream server) ==="

    # Download and extract
    echo "Downloading MediaMTX $version for $arch..."
    curl -L "$binary_url" | tar xz -C "$tmpdir"

    # Install binary
    sudo mv "$tmpdir/mediamtx" "$MEDIAMTX_INSTALL_DIR/mediamtx"
    sudo chmod +x "$MEDIAMTX_INSTALL_DIR/mediamtx"

    # Install config file
    if [ -f "$MEDIAMTX_CONFIG" ]; then
        sudo cp "$MEDIAMTX_CONFIG" /etc/mediamtx.yml
        echo "Config file installed to /etc/mediamtx.yml"
    else
        echo "Warning: $MEDIAMTX_CONFIG not found – using default config"
    fi

    # Optional systemd service
    echo "Creating systemd service (requires sudo)..."
    sudo tee /etc/systemd/system/${MEDIAMTX_SERVICE_NAME}.service >/dev/null <<EOF
[Unit]
Description=MediaMTX streaming server
After=network.target

[Service]
ExecStart=$MEDIAMTX_INSTALL_DIR/mediamtx /etc/mediamtx.yml
Restart=on-failure
User=pi

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable "$MEDIAMTX_SERVICE_NAME"
    echo "MediaMTX service enabled. Start with: sudo systemctl start $MEDIAMTX_SERVICE_NAME"
    echo "Or use './pcjr.sh server-start'"

    rm -rf "$tmpdir"
}

server-start() {
    # Starts the server using systemd if available, else runs directly
    if systemctl is-active --quiet "$MEDIAMTX_SERVICE_NAME"; then
        echo "MediaMTX is already running."
    elif systemctl list-unit-files | grep -q "^${MEDIAMTX_SERVICE_NAME}.service"; then
        sudo systemctl start "$MEDIAMTX_SERVICE_NAME"
        echo "Started MediaMTX service."
    else
        echo "Starting MediaMTX directly (Ctrl+C to stop)..."
        $MEDIAMTX_INSTALL_DIR/mediamtx "$MEDIAMTX_CONFIG"
    fi
}

echo_text() {
    if [ $# -eq 0 ]; then
        echo "Usage: ./pcjr.sh echo <text>"
        exit 1
    fi
    stty -F "$SERIAL_DEVICE" "$SERIAL_BAUD" raw -clocal -hupcl -echo
    echo "$*" > "$SERIAL_DEVICE"
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
  sniff               Start serial sniffing (blocking)
  stream              Open mpv to view the RTSP camera stream
  server-setup        Install MediaMTX and configure the camera server
  server-start        Start the MediaMTX server (systemd or foreground)
  echo <text>         Send text to the PCjr keyboard
  driver [args...]    Run the Python interactive keyboard driver
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
    sniff)          sniff ;;
    stream)         stream ;;
    server-setup)   server-setup ;;
    server-start)   server-start ;;
    echo)           shift; echo_text "$@" ;;
    driver)         shift; driver "$@" ;;
    help|--help|-h) help_msg ;;
    *)              echo "Unknown command: $1" >&2; help_msg; exit 1 ;;
esac

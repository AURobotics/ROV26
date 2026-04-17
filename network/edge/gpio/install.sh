#!/bin/bash

if [ "$EUID" -ne 0 ]; then
    echo "Starting the script with administrator privileges.."
    exec sudo "$0" "$@"
    echo "Failed to start with administrator privileges, exiting.."
    exit 1
fi


SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 ; pwd -P)
OPT_DIR="/opt/gpio"
SERVICE_FILE="/etc/systemd/system/gpio-server.service"


if ! command -v gpioset >/dev/null 2>&1; then
    apt update
    apt install gpiod
fi

if ! command -v socat >/dev/null 2>&1; then
    apt update
    apt install socat
fi

echo "Setting up $OPT_DIR ..."
mkdir -p "$OPT_DIR/presets/"
cp "$SCRIPT_DIR/runner" "$OPT_DIR/runner"
chmod +x "$OPT_DIR/runner"

echo "Copying preset sequences..."
cp "$SCRIPT_DIR/presets/"* "$OPT_DIR/presets/"*
chmod +x "$OPT_DIR/presets/"*

echo "Installing systemd service..."
cp "$SCRIPT_DIR/gpio-server.service" "$SERVICE_FILE"
systemctl reset-failed gpio-server
systemctl enable gpio-server
systemctl start gpio-server
systemctl daemon-reload
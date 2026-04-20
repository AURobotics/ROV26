#!/bin/bash

if [ "$EUID" -ne 0 ]; then
    echo "Starting the script with administrator privileges.."
    exec sudo "$0" "$@"
    echo "Failed to start with administrator privileges, exiting.."
    exit 1
fi

OPT_DIR="/opt/ustreamer"
UDEV_RULE_FILE="/etc/udev/rules.d/99-camera-stream.rules"
SERVICE_FILE="/etc/systemd/system/ustreamer@.service"

echo "Starting uStreamer service cleanup (leaving system packages intact)..."

echo "Removing udev rules..."
rm -f "$UDEV_RULE_FILE"
udevadm control --reload-rules
udevadm trigger --subsystem-match=video4linux --action=change

echo "Stopping and disabling systemd services..."
systemctl stop "ustreamer@*" 2>/dev/null
rm -f "$SERVICE_FILE"
systemctl daemon-reload

echo "Removing settings..."
rm -rf "$OPT_DIR"

echo "uStreamer service cleanup complete."
exit 0
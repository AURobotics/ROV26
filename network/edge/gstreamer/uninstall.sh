#!/bin/bash

if [ "$EUID" -ne 0 ]; then
    echo "Starting the script with administrator privileges.."
    exec sudo "$0" "$@"
    echo "Failed to start with administrator privileges, exiting.."
    exit 1
fi

OPT_DIR="/opt/gstreamer"
UDEV_RULE_FILE="/etc/udev/rules.d/99-camera-gst.rules"
SERVICE_FILE="/etc/systemd/system/gst-stream@.service"
TOGGLE_SCRIPT="/usr/bin/toggle-gstreamer-service"

echo "Starting GStreamer service cleanup (leaving GStreamer packages intact)..."

echo "Removing udev rules..."
rm -f "$UDEV_RULE_FILE"
udevadm control --reload-rules
udevadm trigger --subsystem-match=video4linux --action=change

echo "Stopping and disabling systemd services..."
systemctl stop "gst-stream@*" 2>/dev/null
rm -f "$SERVICE_FILE"
systemctl daemon-reload

echo "Removing scripts and settings..."
rm -f "$TOGGLE_SCRIPT"
rm -rf "$OPT_DIR"

echo "GStreamer service cleanup complete."
exit 0
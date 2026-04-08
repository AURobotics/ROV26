#!/bin/bash

SERVICE_FILE="/etc/systemd/system/vhusbd.service"
OPT_DIR="/opt/vhusbd/"

if [ "$EUID" -ne 0 ]; then
    echo "Starting the script with administrator privileges.."
    exec sudo "$0" "$@"
    echo "Failed to start with administrator privileges, exiting.."
    exit 1
fi

echo "Stopping and disabling systemd services..."
systemctl stop "vhusbd.service" 2>/dev/null
rm -f "$SERVICE_FILE"
systemctl daemon-reload

echo "Removing script and files..."
rm -rf "$OPT_DIR"

echo "vhusbd uninstall complete."
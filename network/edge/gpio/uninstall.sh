#!/bin/bash

if [ "$EUID" -ne 0 ]; then
    echo "Starting the script with administrator privileges.."
    exec sudo "$0" "$@"
    echo "Failed to start with administrator privileges, exiting.."
    exit 1
fi


OPT_DIR="/opt/gpio"
SERVICE_FILE="/etc/systemd/system/gpio-server.service"

echo "Uninstalling systemd service..."
systemctl stop gpio-server 2>/dev/null
systemctl disable gpio-server 2>/dev/null
rm -f "$SERVICE_FILE"
systemctl daemon-reload


echo "Cleaning up $OPT_DIR ..."
rm -rf "$OPT_DIR"
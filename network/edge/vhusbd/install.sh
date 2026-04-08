#!/bin/bash

SERVICE_FILE="/etc/systemd/system/vhusbd.service"
EXECUTABLE="/opt/vhusbd/vhusbd"
OPT_DIR="/opt/vhusbd/"

if [ "$EUID" -ne 0 ]; then
    echo "Starting the script with administrator privileges.."
    exec sudo "$0" "$@"
    echo "Failed to start with administrator privileges, exiting.."
    exit 1
fi

echo "Creating vhusbd directories.."
mkdir -p "$OPT_DIR"

if [ ! -f "$EXECUTABLE" ]; then
    ARCH=$(uname -m)

    case "$ARCH" in
        x86_64)
            VHUSBD_DL="https://www.virtualhere.com/sites/default/files/usbserver/vhusbdx86_64"
            ;;
        aarch64|arm64)
            VHUSBD_DL="https://www.virtualhere.com/sites/default/files/usbserver/vhusbdarm64"
            ;;
        armv7l)
            VHUSBD_DL="https://www.virtualhere.com/sites/default/files/usbserver/vhusbdarm"
            ;;
        *)
            echo "Unsupported Architecture: $ARCH"
            exit 1
            ;;
    esac
    echo "Downloading vhusbd.."
    if wget -q "$VHUSBD_DL" -O "$EXECUTABLE"; then
        chmod +x "$EXECUTABLE"
    else
        echo "Download failed, cleaning up.."
        cleanup
        exit 1
    fi
fi

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 ; pwd -P)

echo "Installing the systemd service.."
cp "$SCRIPT_DIR/vhusbd.service" "$SERVICE_FILE"
systemctl daemon-reload
systemctl start vhusbd.service
systemctl enable vhusbd.service

echo "vhusbd setup complete."
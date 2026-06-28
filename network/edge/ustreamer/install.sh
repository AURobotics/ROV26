#!/bin/bash

if [ "$EUID" -ne 0 ]; then
    echo "Starting the script with administrator privileges.."
    exec sudo "$0" "$@"
    echo "Failed to start with administrator privileges, exiting.."
    exit 1
fi


SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 ; pwd -P)
OPT_DIR="/opt/ustreamer"
UDEV_RULE_FILE="/etc/udev/rules.d/99-camera-stream.rules"
UDEV_RULE='ACTION=="add", SUBSYSTEM=="video4linux", ENV{ID_V4L_CAPABILITIES}=="*:capture:*", ENV{ID_V4L_IS_HW_NODE}!="1", TAG+="systemd", ENV{SYSTEMD_WANTS}+="ustreamer@%k.service"'
SERVICE_FILE="/etc/systemd/system/ustreamer@.service"

echo "Checking for uStreamer..."
if ! command -v ustreamer >/dev/null 2>&1; then
    echo "uStreamer is missing..."
    [ -f /etc/os-release ] && . /etc/os-release
    if [[ "$ID" == "ubuntu" ]]; then
        echo "Detected Ubuntu. Installing packages..."
        apt update && apt install -y ustreamer
    else
        echo "Please install the equivalent packages using your system's package manager: ustreamer"
        exit 1
    fi
fi


echo "Setting up $OPT_DIR..."
mkdir -p "$OPT_DIR"
cp "$SCRIPT_DIR/runner" "$OPT_DIR/runner"
chmod +x "$OPT_DIR/runner"

echo "Installing systemd service..."
cp "$SCRIPT_DIR/ustreamer@.service" "$SERVICE_FILE"
systemctl reset-failed "ustreamer@*"
systemctl daemon-reload

echo "Installing udev rules, for customization please edit the script..."
echo "$UDEV_RULE" > "$UDEV_RULE_FILE"
udevadm control --reload-rules
udevadm trigger --subsystem-match=video4linux --action=add

echo "uStreamer setup complete."

#!/bin/bash

if [ "$EUID" -ne 0 ]; then
    echo "Starting the script with administrator privileges.."
    exec sudo "$0" "$@"
    echo "Failed to start with administrator privileges, exiting.."
    exit 1
fi


SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 ; pwd -P)
OPT_DIR="/opt/gstreamer"
UDEV_RULE_FILE="/etc/udev/rules.d/99-camera-gst.rules"
UDEV_RULE='ACTION=="add", SUBSYSTEM=="video4linux", ENV{ID_V4L_CAPABILITIES}=="*:capture:*", ENV{ID_V4L_IS_HW_NODE}!="1", TAG+="systemd", ENV{SYSTEMD_WANTS}+="gst-stream@%k.service"'
SERVICE_FILE="/etc/systemd/system/gst-stream@.service"
TOGGLE_SCRIPT="/usr/bin/toggle-gstreamer-service"


GST_ELEMENTS=("videoconvert" "jpegdec" "x264enc" "rtph264pay" "vaapih264enc" "avdec_h264")
GST_PACKAGES_UBUNTU=("gstreamer1.0-plugins-base" "gstreamer1.0-plugins-good" "gstreamer1.0-plugins-bad" "gstreamer1.0-plugins-ugly" "gstreamer1.0-libav" "gstreamer1.0-vaapi" "gstreamer1.0-tools" "libgstreamer1.0-dev")

check_gst_requirements() {
    echo "Checking GStreamer Capabilities..."
    if ! command -v gst-launch-1.0 >/dev/null 2>&1; then return 1; fi
    gst-inspect-1.0 "${GST_ELEMENTS[@]}" >/dev/null 2>&1
}

if ! check_gst_requirements; then
    echo "GStreamer or some elements are missing..."
    [ -f /etc/os-release ] && . /etc/os-release
    if [[ "$ID" == "ubuntu" ]]; then
        echo "Detected Ubuntu. Installing packages..."
        apt update && apt install -y "${GST_PACKAGES_UBUNTU[@]}"
    else
        echo "Please install the equivalent packages using your system's package manager: ${GST_PACKAGES_UBUNTU[@]}"
        exit 1
    fi
fi

echo "Setting up /opt/gstreamer..."
mkdir -p "$OPT_DIR/settings"
echo "640,480" > "$OPT_DIR/settings/resolution"

cp "$SCRIPT_DIR/runner" "$OPT_DIR/runner"
chmod +x "$OPT_DIR/runner"

echo "Installing systemd service..."
cp "$SCRIPT_DIR/gst-stream@.service" "$SERVICE_FILE"
systemctl reset-failed "gst-stream@*"
systemctl daemon-reload

echo "Installing udev rules, for customization please edit the script..."
echo "$UDEV_RULE" > "$UDEV_RULE_FILE"
udevadm control --reload-rules
udevadm trigger --subsystem-match=video4linux --action=add

echo "Installing the toggling script 'toggle-gstreamer-service'..."
cp "$SCRIPT_DIR/toggle-gstreamer-service" "$TOGGLE_SCRIPT"
chmod +x "$TOGGLE_SCRIPT"

echo "GStreamer setup complete."

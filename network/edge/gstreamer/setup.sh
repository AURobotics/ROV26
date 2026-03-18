#!/bin/bash


if [ "$EUID" -ne 0 ]; then
    echo "Restarting the script with administrator privileges.."
    exec sudo "$0" "$@"
    exit 1
fi


SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 ; pwd -P)
OPT_DIR="/opt/gstreamer"
UDEV_RULE_FILE="/etc/udev/rules.d/99-camera-gst.rules"
# UDEV_RULE='ACTION=="add", SUBSYSTEM=="video4linux", ENV{ID_VENDOR_ID}=="1bcf", ENV{ID_MODEL_ID}=="0c45", ENV{ID_V4L_CAPABILITIES}=="*:capture:*", TAG+="systemd", ENV{SYSTEMD_WANTS}+="gst-stream@%k.service'
UDEV_RULE='ACTION=="add", SUBSYSTEM=="video4linux", ENV{ID_V4L_CAPABILITIES}=="*:capture:*", ENV{ID_V4L_IS_HW_NODE}!="1", TAG+="systemd", ENV{SYSTEMD_WANTS}+="gst-stream@%k.service"'
SERVICE_FILE="/etc/systemd/system/gst-stream@.service"
PAUSE_SCRIPT="/usr/bin/pause-camera-autostart"


cleanup() {
    echo "Starting GStreamer cleanup (leaving GStreamer packages intact)..."

    echo "Stopping and disabling GStreamer services..."
    systemctl stop "gst-stream@*" 2>/dev/null
    rm -f "$SERVICE_FILE"
    systemctl daemon-reload

    echo "Removing udev rules..."
    rm -f "$UDEV_RULE_FILE"
    udevadm control --reload-rules
    udevadm trigger

    echo "Removing scripts and settings..."
    rm -f "$PAUSE_SCRIPT"
    rm -rf "$OPT_DIR"

    echo "GStreamer cleanup complete."
    exit 0
}

# Check for cleanup mode flag
case "$1" in
    --cleanup|-c)
        cleanup
        ;;
esac

# --- INSTALLATION LOGIC STARTS HERE ---

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

echo "Setting up /opt/gstreamer..."
mkdir -p "$OPT_DIR/settings"
echo "640,480" > "$OPT_DIR/settings/resolution"

cp "$SCRIPT_DIR/runner" "$OPT_DIR/runner"
chmod +x "$OPT_DIR/runner"

echo "Installing udev rules, for customization please edit the script..."
echo "$UDEV_RULE" > "$UDEV_RULE_FILE"
udevadm control --reload-rules && udevadm trigger

echo "Installing systemd service..."
cp "$SCRIPT_DIR/gst-stream@.service" "$SERVICE_FILE"
systemctl daemon-reload

echo "Installing pause script..."
cp "$SCRIPT_DIR/pause-camera-autostart" "$PAUSE_SCRIPT"
chmod +x "$PAUSE_SCRIPT"

echo "GStreamer setup complete."
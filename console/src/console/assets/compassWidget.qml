pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Shapes

Rectangle {
    id: root
    width: 300
    height: 300
    antialiasing: true
    // Guard against uninitialized palette
    color: (palette && palette.window) ? palette.window : "#2c3e50"
    
    // Internal helper to simplify null-checking the Python object
    readonly property real currentBearing: rov ? rov.bearing : 0.0

    Rectangle {
        id: bezelRing
        width: Math.min(parent.width, parent.height)
        height: width
        anchors.centerIn: parent
        radius: width / 2
        
        // Safe palette check
        property bool isDark: (palette && palette.window.hsvValue < 0.5)
        color: isDark ? "white" : "#1f1f1f"
        border.color: isDark ? "#95a5a6" : "#555555"
        border.width: 10

        Item {
            id: rotatingDial
            anchors.fill: parent
            anchors.margins: parent.border.width

            // Use the helper property to ensure it's never [undefined]
            rotation: -root.currentBearing

            Behavior on rotation {
                RotationAnimation {
                    direction: RotationAnimation.Shortest
                    duration: 150
                    easing.type: Easing.OutQuad
                }
            }

            Repeater {
                model: 36
                delegate: Item {
                    id: tickContainer
                    required property int index
                    anchors.fill: parent
                    rotation: index * 10

                    Rectangle {
                        width: (tickContainer.index % 9 === 0) ? 4 : 2
                        height: 15
                        color: (tickContainer.index % 9 === 0) ? "#e74c3c" : "#cccccc"
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: 5
                    }

                    Text {
                        text: {
                            if (tickContainer.index === 0) return "N";
                            if (tickContainer.index === 9) return "E";
                            if (tickContainer.index === 18) return "S";
                            if (tickContainer.index === 27) return "W";
                            return ""; // Return empty string instead of undefined
                        }
                        color: root.isDark ? "#333333" : "#dddddd"
                        font.pixelSize: (tickContainer.index % 9 === 0) ? 24 : 16
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: 25
                        rotation: -tickContainer.rotation
                    }
                }
            }
        }

        // Fixed Indicator (Triangle)
        Shape {
            width: 20
            height: 20
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: parent.border.width + 10
            z: 10
            ShapePath {
                strokeWidth: 0
                fillColor: "#cccccc"
                startX: 10; startY: 0
                PathLine { x: 0; y: 20 }
                PathLine { x: 20; y: 20 }
                PathLine { x: 10; y: 0 }
            }
        }

        // Center Heading Readout
        Rectangle {
            anchors.centerIn: parent
            width: 80
            height: 40
            radius: 10
            color: "#cc000000"

            Text {
                anchors.centerIn: parent
                // Explicitly cast to string to avoid "Unable to assign [undefined] to QString"
                text: root.currentBearing.toFixed(0).toString() + "°"
                color: "white"
                font.pixelSize: 20
                font.bold: true
            }
        }
    }
}
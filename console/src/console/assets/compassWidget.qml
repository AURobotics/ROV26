import QtQuick
import QtQuick.Controls
import QtQuick.Shapes

pragma ComponentBehavior: Bound

Item {
    id: root
    width: 300
    height: 300

    Rectangle {
        id: bezelRing
        width: (parent.width > parent.height) ? parent.height : parent.width
        height: width
        anchors.centerIn: parent
        radius: width / 2 // Makes a perfect circle
        color: "transparent"
        border.color: "#555555"
        border.width: 4
    }
    
    // === THE ROTATING DIAL ===
    Item {
        id: rotatingDial
        anchors.fill: parent
        anchors.margins: 10

        // BINDING: We now point directly to the 'rov' object
        // and its 'bearing' property defined in Python.
        rotation: -rov.bearing

        // This keeps the movement fluid even if Python sends integers
        Behavior on rotation {
            RotationAnimation {
                direction: RotationAnimation.Shortest
                duration: 150 // Snappy but smooth
                easing.type: Easing.OutQuad
            }
        }

        // --- Tick Marks & Labels ---
        Repeater {
            model: 36
            delegate: Item {
                id: tickContainer

                required property int index

                anchors.centerIn: parent
                rotation: index * 10

                Rectangle {
                    width: (tickContainer.index % 9 === 0) ? 4 : 2
                    height: 15
                    color: (tickContainer.index % 9 === 0) ? "#e74c3c" : "#cccccc"
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: -(rotatingDial.height / 2)
                }

                Text {
                    text: {
                        if (tickContainer.index === 0) return "N"
                        if (tickContainer.index === 9) return "E"
                        if (tickContainer.index === 18) return "S"
                        if (tickContainer.index === 27) return "W"
                        return (tickContainer.index * 10).toString()
                    }
                    color: (tickContainer.index % 9 === 0) ? "#e74c3c" : "white"
                    font.pixelSize: (tickContainer.index % 9 === 0) ? 24 : 16
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: -(rotatingDial.height / 2) + 25
                    rotation: -tickContainer.rotation
                }
            }
        }
    }

    // === THE FIXED INDICATOR ===
    Shape {
        width: 20; height: 20
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 5
        z: 10
        ShapePath {
            strokeWidth: 1; strokeColor: "#e74c3c"; fillColor: "#e74c3c"
            startX: 10; startY: 20
            PathLine { x: 0; y: 0 }
            PathLine { x: 20; y: 0 }
            PathLine { x: 10; y: 20 }
        }
    }

    // === Center Heading Readout ===
    Rectangle {
        anchors.centerIn: parent
        width: 80; height: 40; radius: 10
        color: "#cc000000"

        Text {
            anchors.centerIn: parent
            // BINDING: Update text readout from Python property
            text: rov.bearing.toFixed(0) + "°"
            color: "white"
            font.pixelSize: 20; font.bold: true
        }
    }
}
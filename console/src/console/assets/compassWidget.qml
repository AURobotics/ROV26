pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Shapes

Rectangle {
    id: root

    property real bearing: rov ? rov.bearing : 0

    width: 240
    height: 240
    antialiasing: true
    color: palette.window
    
    Rectangle {
        id: bezelRing
        width: (parent.width > parent.height) ? parent.height : parent.width
        height: width
        anchors.centerIn: parent
        radius: width / 2
        color: (palette.window.hsvValue > 0.5) ? "#1f1f1f" : "white"
        border.color: (palette.window.hsvValue > 0.5) ? "#555555" : "#95a5a6"
        border.width: 10

        Item {
            id: rotatingDial
            anchors.fill: parent
            anchors.margins: parent.border.width

            rotation: -root.bearing

            Behavior on rotation {
                RotationAnimation {
                    direction: RotationAnimation.Shortest
                    duration: 150
                    easing.type: Easing.OutQuad
                }
            }

            //Tick Marks & Labels
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
                            if (tickContainer.index === 0)
                                return "N";
                            if (tickContainer.index === 9)
                                return "E";
                            if (tickContainer.index === 18)
                                return "S";
                            if (tickContainer.index === 27)
                                return "W";
                            return "";
                        }
                        color: (palette.window.hsvValue > 0.5) ? "#dddddd" : "#333333"
                        font.pixelSize: (tickContainer.index % 9 === 0) ? 24 : 16
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: 25
                        rotation: -tickContainer.rotation
                    }
                }
            }
        }

        // === THE FIXED INDICATOR ===
        Shape {
            width: 20
            height: 20
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: parent.border.width + 10
            z: 10
            ShapePath {
                strokeWidth: 0
                strokeColor: "black"
                fillColor: "#cccccc"
                startX: 10
                startY: 0
                PathLine {
                    x: 0
                    y: 20
                }
                PathLine {
                    x: 20
                    y: 20
                }
                PathLine {
                    x: 10
                    y: 0
                }
            }
        }

        // === Center Heading Readout ===
        Rectangle {
            anchors.centerIn: parent
            width: 80
            height: 40
            radius: 10
            color: "#cc000000"

            Text {
                anchors.centerIn: parent
                // BINDING: Update text readout from Python property
                text: root.bearing.toFixed(0) + "°"
                color: "white"
                font.pixelSize: 20
                font.bold: true
            }
        }
    }
}

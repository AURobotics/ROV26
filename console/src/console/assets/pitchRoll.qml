import QtQuick
import QtQuick.Controls
import QtQuick.Shapes
import Qt5Compat.GraphicalEffects

pragma ComponentBehavior: Bound

Item {
    id: rootWidget
    width: 300
    height: 300
    antialiasing: true

    Rectangle {
        id: bezelRing
        width: parent.width < parent.height ? parent.width : parent.height
        height: width
        anchors.centerIn: parent
        radius: width / 2 // Makes a perfect circle
        color: "transparent"
        border.color: "#555555"
        border.width: 15

        Repeater {
            model: 36
            delegate: Item {
                id: tickContainer

                required property int index

                anchors.fill: parent
                rotation: index * 10

                Rectangle {
                    width: (tickContainer.index % 9 === 0) ? 4 : 2
                    height: 10
                    color: (tickContainer.index % 9 === 0) ? "#e74c3c" : "#cccccc"
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.topMargin: 5
                }
            }
        }
    }

    Rectangle {
        id: pitchIndicator
        width: bezelRing.width - 2 * bezelRing.border.width
        height: width
        anchors.centerIn: parent
        color: "#62c1e5"
        radius: width / 2

        layer.enabled: true
        layer.effect: OpacityMask {
            maskSource: Rectangle {
                width: pitchIndicator.width
                height: pitchIndicator.height
                radius: pitchIndicator.radius
            }
        }

        rotation: -rov.roll
        Behavior on rotation {
            RotationAnimation {
                direction: RotationAnimation.Shortest
                duration: 150 // Snappy but smooth
                easing.type: Easing.OutQuad
            }
        }

        Rectangle {
            id: groundPlane
            width: parent.width
            height: Math.max(0, Math.min(parent.height * (0.5 - rov.pitch / rov.pitchFOV), parent.height)) // Map pitch to vertical position
            color: "#C45A3D"
            anchors.bottom: parent.bottom
            
            Behavior on height {
                NumberAnimation {
                    duration: 150
                    easing.type: Easing.OutQuad
                }
            }
        }

        Item {
            id: pitchScale
            anchors.centerIn: parent

            // This container moves the whole ladder up and down based on the current pitch
            property real pixelsPerDegree: parent.height / rov.pitchFOV
            anchors.verticalCenterOffset: (rov.pitch * pixelsPerDegree)

            Repeater {
                // Range from -60 to 60, every 5 degrees
                model: [-60, -55, -50, -45, -40, -35, -30, -25, -20, -15, -10, -5, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]

                delegate: Item {
                    required property int modelData

                    anchors.centerIn: parent
                    anchors.verticalCenterOffset: -(modelData * pitchScale.pixelsPerDegree)

                    // The horizontal line
                    Rectangle {
                        anchors.centerIn: parent
                        width: Math.abs(modelData) % 10 === 0 ? 60 : 30 // Major lines are wider
                        height: 2
                        color: "white"
                    }

                    // The degree text
                    Text {
                        anchors.centerIn: parent
                        anchors.horizontalCenterOffset: -40
                        text: Math.abs(modelData) %10 === 0 ? Math.abs(modelData) : "" // Only show text for major lines
                        color: "white"
                        font.pixelSize: 12
                    }
                    Text {
                        anchors.centerIn: parent
                        anchors.horizontalCenterOffset: 40
                        text: Math.abs(modelData) %10 === 0 ? Math.abs(modelData) : "" // Only show text for major lines
                        color: "white"
                        font.pixelSize: 12
                    }
                }
            }
        }

        Shape {
            id: rollPointer
            width: 20
            height: 20
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 5
            z: 10
            ShapePath {
                strokeWidth: 1
                strokeColor: "black"
                fillColor: "white"
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

        // Center dot and reticle
        Rectangle {
            id: centerDot
            width: 6
            height: width
            radius: width / 2
            color: "red"
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
        }
        Rectangle {
            id: centerReticleLeft
            width: 30
            height: 6
            color: "red"
            anchors.centerIn: parent
            anchors.horizontalCenterOffset: -40
        }
        Rectangle {
            id: centerReticleRight
            width: 30
            height: 6
            color: "red"
            anchors.centerIn: parent
            anchors.horizontalCenterOffset: 40
        }
    }
}

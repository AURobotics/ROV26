import QtQuick
import QtQuick.Particles

Rectangle {
    id: root
    property real thrustLevel: 0 // Range from -1 (full reverse) to 1 (full forward)
    property real baseRotation: 0
    width: 50; height: 100
    rotation: (thrustLevel > 0) ? baseRotation : (baseRotation + 180) % 360 // Rotate 180 degrees if thrust is negative
    border.width: 2
    border.color: "#555555"
    color: "white"

    Rectangle {
        id: thrustFill
        width: parent.width - parent.border.width * 2
        height: (parent.height - parent.border.width * 2) * Math.abs(root.thrustLevel)
        anchors.bottom: parent.bottom
        anchors.bottomMargin: parent.border.width
        anchors.horizontalCenter: parent.horizontalCenter
        color: "#00ff80"
        Behavior on height { NumberAnimation { duration: 150 } }
    }

    ParticleSystem {
        id: particles
        width: parent.width - parent.border.width * 2
        height: 0
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height // Start at the "exhaust"
        running: true

        Emitter {
            width: parent.width
            velocity: AngleDirection {
                angle: 90; angleVariation: 15; magnitude: 100 * Math.abs(root.thrustLevel)
            }
            lifeSpan: 1000
            emitRate: 40 * Math.abs(root.thrustLevel)
            size: 12
            sizeVariation: 6
        }

        ImageParticle {
            source: "qrc:///particleresources/fuzzydot.png"
            color: "#6000ff80"
        }
    }
}
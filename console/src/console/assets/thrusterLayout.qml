import QtQuick
import QtQuick.Controls
import QtQuick.Shapes
import QtQuick.Particles

pragma ComponentBehavior: Bound

Item {
    id: rootWidget
    width: 300
    height: 300
    antialiasing: true

    HorizontalThruster {
        id: horizontalThruster1
        x: parent.width / 4 - width / 2
        y: parent.height / 4 - height / 2
        baseRotation: 45
        thrustLevel: rov.thrustLevel1
    }
    HorizontalThruster {
        id: horizontalThruster2
        x: parent.width * 3 / 4 - width / 2
        y: parent.height / 4 - height / 2
        baseRotation: -45
        thrustLevel: rov.thrustLevel2
    }
    HorizontalThruster {
        id: horizontalThruster3
        x: parent.width / 4 - width / 2
        y: parent.height * 3 / 4 - height / 2
        baseRotation: -45
        thrustLevel: rov.thrustLevel3
    }
    HorizontalThruster {
        id: horizontalThruster4
        x: parent.width * 3 / 4 - width / 2
        y: parent.height * 3 / 4 - height / 2
        baseRotation: 45
        thrustLevel: rov.thrustLevel4
    }
    VerticalThruster {
        id: verticalThruster1
        x: parent.width * 0.4 - width / 2
        y: parent.height * 1/3 - height / 2
        thrustLevel: rov.thrustLevel5
    }
    VerticalThruster {
        id: verticalThruster2
        x: parent.width * 0.6 - width / 2
        y: parent.height * 1/3 - height / 2
        thrustLevel: rov.thrustLevel5
    }
    VerticalThruster {
        id: verticalThruster3
        x: parent.width * 0.4 - width / 2
        y: parent.height * 2/3 - height / 2
        thrustLevel: rov.thrustLevel5
    }
    VerticalThruster {
        id: verticalThruster4
        x: parent.width * 0.6 - width / 2
        y: parent.height * 2/3 - height / 2
        thrustLevel: rov.thrustLevel5
    }

    DirectionArrow {
        id: directionArrow
        anchors.centerIn: parent
        rotation: 90 - rov.horizontalAngle
        totalMagnitude: rov.totalHorizontalThrust / (2 * Math.sqrt(2)) // Normalize to max possible thrust
    }
}
import QtQuick
import QtQuick.Controls
import QtQuick.Shapes
import QtQuick.Particles

pragma ComponentBehavior: Bound

Rectangle {
    id: root
    width: 480
    height: 240
    antialiasing: true
    color: palette.window

    property real hThrust1: rov? rov.h_thrust1 : 0
    property real hThrust2: rov? rov.h_thrust2 : 0
    property real hThrust3: rov? rov.h_thrust3 : 0
    property real hThrust4: rov? rov.h_thrust4 : 0
    property real vThrust1: rov? rov.v_thrust1 : 0
    property real vThrust2: rov? rov.v_thrust2 : 0
    property real vThrust3: rov? rov.v_thrust3 : 0
    property real vThrust4: rov? rov.v_thrust4 : 0

    property real horizontalAngle: rov? rov.horizontalAngle : 90
    property real totalHorizontalThrust: rov? rov.totalHorizontalThrust : 0

    HorizontalThruster {
        id: horizontalThruster1
        x: parent.width / 4 - width / 2
        y: parent.height / 4 - height / 2
        baseRotation: 45
        thrustLevel: root.hThrust1
    }
    HorizontalThruster {
        id: horizontalThruster2
        x: parent.width * 3 / 4 - width / 2
        y: parent.height / 4 - height / 2
        baseRotation: -45
        thrustLevel: root.hThrust2
    }
    HorizontalThruster {
        id: horizontalThruster3
        x: parent.width / 4 - width / 2
        y: parent.height * 3 / 4 - height / 2
        baseRotation: -45
        thrustLevel: root.hThrust3
    }
    HorizontalThruster {
        id: horizontalThruster4
        x: parent.width * 3 / 4 - width / 2
        y: parent.height * 3 / 4 - height / 2
        baseRotation: 45
        thrustLevel: root.hThrust4
    }
    VerticalThruster {
        id: verticalThruster1
        x: parent.width * 0.4 - width / 2
        y: parent.height * 1/3 - height / 2
        thrustLevel: root.vThrust1
    }
    VerticalThruster {
        id: verticalThruster2
        x: parent.width * 0.6 - width / 2
        y: parent.height * 1/3 - height / 2
        thrustLevel: root.vThrust2
    }
    VerticalThruster {
        id: verticalThruster3
        x: parent.width * 0.4 - width / 2
        y: parent.height * 2/3 - height / 2
        thrustLevel: root.vThrust3
    }
    VerticalThruster {
        id: verticalThruster4
        x: parent.width * 0.6 - width / 2
        y: parent.height * 2/3 - height / 2
        thrustLevel: root.vThrust4
    }

    DirectionArrow {
        id: directionArrow
        anchors.centerIn: parent
        rotation: 90 - root.horizontalAngle
        totalMagnitude: root.totalHorizontalThrust / (2 * Math.sqrt(2)) // Normalize to max possible thrust
    }
}
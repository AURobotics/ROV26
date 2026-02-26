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
    
}
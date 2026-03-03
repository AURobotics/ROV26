import QtQuick

Rectangle {
    id: root
    property real thrustLevel: 0 // Range from -1 (full reverse) to 1 (full forward)
    width: 70; height: width
    radius: width / 2
    border.width: 2
    border.color: "#555555"
    color: "white"

    Rectangle {
        id: thrustFill
        width: parent.width - parent.border.width * 2
        height: width
        radius: width / 2
        anchors.centerIn: parent
        color: root.thrustLevel > 0 ? "#00ff80" : "transparent"
        border.color: root.thrustLevel < 0 ? "#00ff80" : "white"
        border.width: root.thrustLevel < 0 ? (width / 2 * Math.abs(root.thrustLevel)) : ((width / 2) * (1 - root.thrustLevel))
    }
    Text {
        visible: Math.abs(root.thrustLevel) > 0.05
        anchors.centerIn: parent
        color: "black"
        text: root.thrustLevel > 0 ? "Up" : "Down"
    }
}
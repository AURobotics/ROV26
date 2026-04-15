pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Shapes
import Qt5Compat.GraphicalEffects

Rectangle {
    id: root

    property real depth: rov ? rov.depth : 0
    property real maxDepth: rov ? rov.max_depth : 1

    width: 42
    height: 240
    color: palette.window

    Rectangle {
        id: depthView

        anchors.centerIn: parent
        height: parent.height
        width: Math.min(42, parent.width)
        radius: 10
        antialiasing: true
        color: "#62c1e5"
        border.color: (palette.window.hsvValue > 0.5) ? "#444444" : "#555555"
        border.width: 5

        layer.enabled: true
        layer.effect: OpacityMask {
            maskSource: Rectangle {
                anchors.centerIn: parent
                width: depthView.width - 2 * depthView.border.width
                height: depthView.height - 2 * depthView.border.width
                radius: depthView.radius
            }
        }

        Item {
            id: depthScale
            anchors.fill: parent
            anchors.margins: parent.border.width

            Repeater {
                model: 4 * root.maxDepth - 1
                delegate: Item {
                    id: tickContainer

                    required property int index

                    anchors.fill: parent

                    Rectangle {
                        width: ((tickContainer.index + 1) % 2 === 0) ? 10 : 5
                        height: 2
                        color: "white"
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.top
                        anchors.verticalCenterOffset: ((tickContainer.index + 1) / (4 * root.maxDepth)) * parent.height
                    }

                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: 15
                        anchors.verticalCenter: parent.top
                        anchors.verticalCenterOffset: ((tickContainer.index + 1) / (4 * root.maxDepth)) * parent.height
                        text: ((tickContainer.index + 1) % 4 === 0) ? (tickContainer.index + 1) / 4 : ""
                        color: "white"
                        font.pixelSize: 12
                    }
                }
            }
        }

        Shape {
            id: depthPointer
            width: 20
            height: 20
            anchors.right: parent.right
            anchors.rightMargin: parent.border.width
            anchors.verticalCenter: parent.top
            anchors.verticalCenterOffset: (root.depth / root.maxDepth) * parent.height
            ShapePath {
                strokeWidth: 0
                fillColor: "#e74c3c"
                startX: 0
                startY: depthPointer.height / 2
                PathLine {
                    x: depthPointer.width
                    y: 0
                }
                PathLine {
                    x: depthPointer.width
                    y: depthPointer.height
                }
                PathLine {
                    x: 0
                    y: depthPointer.height / 2
                }
            }
        }
    }

    Rectangle {
        id: borderOverlay

        anchors.centerIn: parent
        height: depthView.height
        width: depthView.width
        antialiasing: true
        color: "transparent"
        border.color: (palette.window.hsvValue > 0.5) ? "#444444" : "#555555"
        border.width: depthView.border.width
        radius: depthView.radius
    }
}

import QtQuick
import QtQuick.Shapes
import Qt5Compat.GraphicalEffects

Item {
    id: root
    width: 40
    height: 60

    property real totalMagnitude: 0.3 // Range from 0 to 1, controls the fill level of the arrow

    Item {
        id: arrowShape
        anchors.fill: parent
        Rectangle {
            anchors.fill: parent
            color: "white"
        }

        Rectangle {
            id: arrowFill
            width: parent.width
            height: (parent.height) * root.totalMagnitude
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            color: "#62c1e5"
            Behavior on height { NumberAnimation { duration: 150 }}
        }

        layer.enabled: true
        layer.effect: OpacityMask {
            maskSource: Shape {
                width: root.width
                height: root.height
                ShapePath {

                    startX: root.width / 2
                    startY: 0
                    PathLine {
                        x: 0
                        y: root.height * 0.4
                    }
                    PathLine {
                        x: root.width * 0.25
                        y: root.height * 0.4
                    }
                    PathLine {
                        x: root.width * 0.25
                        y: root.height
                    }
                    PathLine {
                        x: root.width * 0.75
                        y: root.height
                    }
                    PathLine {
                        x: root.width * 0.75
                        y: root.height * 0.4
                    }
                    PathLine {
                        x: root.width
                        y: root.height * 0.4
                    }
                    PathLine {
                        x: root.width / 2
                        y: 0
                    }
                }
            }
        }
    }

    Shape {
        id: arrowOutline
        anchors.fill: parent
        ShapePath {
            strokeWidth: 2
            strokeColor: "#555555"
            fillColor: "transparent"
            startX: root.width / 2
            startY: 0
            PathLine {
                x: 0
                y: root.height * 0.4
            }
            PathLine {
                x: root.width * 0.25
                y: root.height * 0.4
            }
            PathLine {
                x: root.width * 0.25
                y: root.height
            }
            PathLine {
                x: root.width * 0.75
                y: root.height
            }
            PathLine {
                x: root.width * 0.75
                y: root.height * 0.4
            }
            PathLine {
                x: root.width
                y: root.height * 0.4
            }
            PathLine {
                x: root.width / 2
                y: 0
            }
        }
    }
}

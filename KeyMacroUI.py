import ujson

from enum import Enum
from pathlib import Path

from PyQt5.QtCore import pyqtSignal, Qt, QPropertyAnimation, QSize, QEvent
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QApplication, QWidget, QFrame, QLabel, QHBoxLayout, QVBoxLayout, QGraphicsOpacityEffect
from qfluentwidgets import MSFluentTitleBar, Icon, FluentIcon, TransparentToolButton, TextWrap
from qfluentwidgets.components.widgets.frameless_window import FramelessWindow
from qfluentwidgets.components.widgets.info_bar import InfoIconWidget

from KeyMacro import KeyMacro


class KeyMacroUI(FramelessWindow):

    def __init__(self):
        super().__init__()
        self.keyMacros: dict[str, KeyMacro] = {}
        self.macrosPath = Path.cwd() / "keyMacros.json"
        self.loadKeyMacros()
        self.__initUI()

    def __initUI(self):
        self.setContentsMargins(0, 35, 0, 10)
        self.setTitleBar(MSFluentTitleBar(self))
        self.setWindowTitle("按按又键键(￣▽￣)")
        self.setWindowIcon(Icon(FluentIcon.FINGERPRINT))
        self.setMaximumSize(1920, 1080)
        self.setMinimumSize(400, 230)
        self.resize(700, 235)

        self.keyMacroContentsUI = self.__loadKeyMacrosUI()

        mainLayout = QVBoxLayout()
        mainLayout.addLayout(self.keyMacroContentsUI)
        self.setLayout(mainLayout)

    def __loadKeyMacrosUI(self):
        contents = QVBoxLayout()
        for name, keyMacro in self.keyMacros:
            macroInfoBar = KeyMacroInfoBar(FluentIcon.QUICK_NOTE, "Script", name, parent=self)
            macroInfoBar.setProperty("id", name)
            macroInfoBar.closedSignal.connect(self.__delKeyMacro)

            contents.addWidget(macroInfoBar)
            contents.addSpacing(10)

        newInfoBar = KeyMacroInfoBar(FluentIcon.ADD_TO, "New", "新建脚本", isClosable=False, parent=self)
        contents.addWidget(newInfoBar)
        return contents

    def __delKeyMacro(self, name: str):
        if name in self.keyMacros:
            self.keyMacros.pop(name)
            self.saveKeyMacros()

    def loadKeyMacros(self):
        if self.macrosPath.exists():
            keyMacros = loadJson(self.macrosPath)
            self.keyMacros = list(keyMacros.values())

    def saveKeyMacros(self):
        if len(self.keyMacros) > 0:
            dumpJson(self.macrosPath, {name: str(km) for name, km in self.keyMacros.items()})

    def closeEvent(self, event):
        self.saveKeyMacros()


class KeyMacroInfoBar(QFrame):
    closedSignal = pyqtSignal(str)

    def __init__(self, icon, title: str, content: str, orient=Qt.Horizontal, isClosable=True, parent=None):
        super().__init__(parent=parent)
        self.icon = icon
        self.title = title
        self.content = content
        self.orient = orient
        self.isClosable = isClosable

        self.__initWidget()

    def __initWidget(self):
        self.titleLabel = QLabel(self)
        self.contentLabel = QLabel(self)
        self.closeButton = TransparentToolButton(FluentIcon.CLOSE, self)
        self.iconWidget = InfoIconWidget(self.icon)

        self.hBoxLayout = QHBoxLayout(self)
        self.textLayout = QHBoxLayout() if self.orient == Qt.Horizontal else QVBoxLayout()
        self.widgetLayout = QHBoxLayout() if self.orient == Qt.Horizontal else QVBoxLayout()

        self.opacityEffect = QGraphicsOpacityEffect(self)
        self.opacityAni = QPropertyAnimation(self.opacityEffect, b'opacity', self)

        self.lightBackgroundColor = None

        self.setFixedHeight(50)
        self.opacityEffect.setOpacity(1)
        self.setGraphicsEffect(self.opacityEffect)

        self.closeButton.setFixedSize(36, 36)
        self.closeButton.setIconSize(QSize(12, 12))
        self.closeButton.setCursor(Qt.PointingHandCursor)
        self.closeButton.setVisible(self.isClosable)

        self.__setQss()
        self.__initLayout()

        self.closeButton.clicked.connect(self.__fadeOut)

    def __initLayout(self):
        self.hBoxLayout.setContentsMargins(6, 6, 6, 6)
        self.hBoxLayout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
        self.textLayout.setSizeConstraint(QHBoxLayout.SetMinimumSize)
        self.textLayout.setAlignment(Qt.AlignTop)
        self.textLayout.setContentsMargins(1, 8, 0, 8)

        self.hBoxLayout.setSpacing(0)
        self.textLayout.setSpacing(5)

        # add icon to layout
        self.hBoxLayout.addWidget(self.iconWidget, 0, Qt.AlignTop | Qt.AlignLeft)

        # add title to layout
        self.textLayout.addWidget(self.titleLabel, 1, Qt.AlignTop)
        self.titleLabel.setVisible(bool(self.title))

        # add content label to layout
        if self.orient == Qt.Horizontal:
            self.textLayout.addSpacing(7)

        self.textLayout.addWidget(self.contentLabel, 1, Qt.AlignTop)
        self.contentLabel.setVisible(bool(self.content))
        self.hBoxLayout.addLayout(self.textLayout)

        # add widget layout
        if self.orient == Qt.Horizontal:
            self.hBoxLayout.addLayout(self.widgetLayout)
            self.widgetLayout.setSpacing(10)
        else:
            self.textLayout.addLayout(self.widgetLayout)

        # add close button to layout
        self.hBoxLayout.addSpacing(12)
        self.hBoxLayout.addWidget(self.closeButton, 0, Qt.AlignTop | Qt.AlignLeft)

        self._adjustText()

    def __setQss(self):
        self.titleLabel.setObjectName('titleLabel')
        self.contentLabel.setObjectName('contentLabel')
        if isinstance(self.icon, Enum):
            self.setProperty('type', self.icon.value)
        self.setStyleSheet("""
        KeyMacroInfoBar {
            border: 1px solid rgb(229, 229, 229);
            border-radius: 6px;
            background-color: rgb(244, 244, 244);
        }

        #titleLabel {
            font: 14px 'Segoe UI', 'Microsoft YaHei', 'PingFang SC';
            font-weight: bold;
            color: black;
            background-color: transparent;
        }

        #contentLabel {
            font: 14px 'Segoe UI', 'Microsoft YaHei', 'PingFang SC';
            color: black;
            background-color: transparent;
        }
        """)

    def __fadeOut(self):
        """ fade out """
        self.opacityAni.setDuration(200)
        self.opacityAni.setStartValue(1)
        self.opacityAni.setEndValue(0)
        self.opacityAni.finished.connect(self.close)
        self.opacityAni.start()

    def _adjustText(self):
        w = 900 if not self.parent() else (self.parent().width() - 50)

        # adjust title
        chars = max(min(w / 10, 120), 30)
        self.titleLabel.setText(TextWrap.wrap(self.title, chars, False)[0])

        # adjust content
        chars = max(min(w / 9, 120), 30)
        self.contentLabel.setText(TextWrap.wrap(self.content, chars, False)[0])
        self.adjustSize()

    def addWidget(self, widget: QWidget, stretch=0):
        """ add widget to info bar """
        self.widgetLayout.addSpacing(6)
        align = Qt.AlignTop if self.orient == Qt.Vertical else Qt.AlignVCenter
        self.widgetLayout.addWidget(widget, stretch, Qt.AlignLeft | align)

    def eventFilter(self, obj, e: QEvent):
        if obj is self.parent():
            if e.type() in [QEvent.Resize, QEvent.WindowStateChange]:
                self._adjustText()

        return super().eventFilter(obj, e)

    def closeEvent(self, e):
        idProperty = self.property("id")
        if idProperty:
            self.closedSignal.emit(idProperty)
        self.deleteLater()
        e.ignore()

    def showEvent(self, e):
        self._adjustText()
        super().showEvent(e)

        if self.parent():
            self.parent().installEventFilter(self)

    def paintEvent(self, e):
        super().paintEvent(e)
        if self.lightBackgroundColor is None:
            return

        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        painter.setBrush(self.lightBackgroundColor)

        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, 6, 6)


# ------------------------------------------Common------------------------------------------ #


def moveCenter(widget: QWidget):
    desktop = QApplication.desktop().availableGeometry()
    w, h = desktop.width(), desktop.height()
    widget.move(w // 2 - widget.width() // 2, h // 2 - widget.height() // 2)


def loadJson(jsonPath: str | Path, mode: str = 'r', encoding: str = 'utf-8') -> dict:
    if not jsonPath.exists():
        raise FileNotFoundError(f'[{jsonPath}] json文件读取失败, 文件不存在!')
    with Path(jsonPath).open(mode, encoding=encoding) as f:
        json = ujson.load(f)
    return json


def dumpJson(jsonPath: str | Path, json: dict, mode: str = 'w', encoding: str = 'utf-8'):
    jsonPath = Path(jsonPath)
    if not jsonPath.parent.exists():
        jsonPath.parent.mkdir(parents=True)
    with Path(jsonPath).open(mode, encoding=encoding) as f:
        ujson.dump(json, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    import sys
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    window = KeyMacroUI()
    moveCenter(window)
    window.show()
    sys.exit(app.exec_())

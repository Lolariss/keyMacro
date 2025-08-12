import keyboard
import ujson

from enum import Enum
from pathlib import Path

from PyQt5.QtCore import pyqtSignal, Qt, QPropertyAnimation, QSize
from PyQt5.QtWidgets import QApplication, QWidget, QFrame, QLabel, QHBoxLayout, QVBoxLayout, QGraphicsOpacityEffect
from qfluentwidgets import MSFluentTitleBar, Icon, FluentIcon, TransparentToolButton, TextWrap, TransparentToggleToolButton, CheckBox, LineEdit
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
        self.setFocusPolicy(Qt.StrongFocus)
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
            macroInfoBar = KeyMacroInfoBar(FluentIcon.QUICK_NOTE, "Script", name, keyMacro, parent=self)
            macroInfoBar.setProperty("id", name)
            macroInfoBar.closedSignal.connect(self.__delKeyMacro)

            contents.addWidget(macroInfoBar)
            contents.addSpacing(10)

        newInfoBar = KeyMacroInfoBar(FluentIcon.ADD_TO, "New", "新建脚本", KeyMacro(), isClosable=False, parent=self)
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
    stoppedSignal = pyqtSignal()
    recordedSignal = pyqtSignal()

    def __init__(self, icon, title: str, content: str, keyMacro: KeyMacro, orient=Qt.Horizontal, isClosable=True, parent=None):
        super().__init__(parent=parent)
        self.icon = icon
        self.title = title
        self.content = content
        self.keyMacro = keyMacro
        self.orient = orient
        self.isClosable = isClosable

        self.__initUI()

    def __initUI(self):
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFixedHeight(75)
        self.stoppedSignal.connect(self.__stopped)

        self.titleLabel = QLabel(self.title)
        self.contentLabel = LabelEdit()
        self.contentLabel.setText(self.content)
        self.contentLabel.textChanged.connect(self.__setContent)
        self.closeButton = TransparentToolButton(FluentIcon.CLOSE)
        self.iconWidget = InfoIconWidget(self.icon)

        self.hBoxLayout = QHBoxLayout(self)
        self.textLayout = QHBoxLayout() if self.orient == Qt.Horizontal else QVBoxLayout()
        self.widgetLayout = QHBoxLayout() if self.orient == Qt.Horizontal else QVBoxLayout()

        self.opacityEffect = QGraphicsOpacityEffect(self)
        self.opacityAni = QPropertyAnimation(self.opacityEffect, b'opacity', self)

        self.opacityEffect.setOpacity(1)
        self.setGraphicsEffect(self.opacityEffect)

        self.recordButton = TransparentToggleToolButton(FluentIcon.PLAY)
        self.recordButton.clicked.connect(self.__recording)

        self.playButton = TransparentToggleToolButton(FluentIcon.PLAY_SOLID)
        self.playButton.clicked.connect(self.__playing)
        if len(self.keyMacro.eventsRecord) <= 0:
            self.playButton.setEnabled(False)

        self.isKeyCheckBox = CheckBox("键盘")
        self.isKeyCheckBox.setChecked(True)

        self.isMouseCheckBox = CheckBox("鼠标")
        self.isMouseCheckBox.setChecked(True)

        self.isLoopCheckBox = CheckBox("循环")

        self.closeButton.setFixedSize(36, 36)
        self.closeButton.setIconSize(QSize(12, 12))
        self.closeButton.setCursor(Qt.PointingHandCursor)
        self.closeButton.setVisible(self.isClosable)
        self.closeButton.clicked.connect(self.__fadeOut)

        self.__setQss()
        self.__initLayout()

    def __initLayout(self):
        self.hBoxLayout.setContentsMargins(6, 6, 6, 6)
        self.textLayout.setAlignment(Qt.AlignVCenter)
        self.textLayout.setContentsMargins(1, 8, 0, 8)

        self.hBoxLayout.setSpacing(0)
        self.textLayout.setSpacing(5)

        # add icon to layout
        self.hBoxLayout.addWidget(self.iconWidget, 0, Qt.AlignVCenter | Qt.AlignLeft)

        # add title to layout
        self.textLayout.addWidget(self.titleLabel, 0, Qt.AlignVCenter | Qt.AlignLeft)
        self.titleLabel.setVisible(bool(self.title))

        # add content label to layout
        if self.orient == Qt.Horizontal:
            self.textLayout.addSpacing(7)

        self.textLayout.addWidget(self.contentLabel, 0, Qt.AlignVCenter | Qt.AlignLeft)
        self.contentLabel.setVisible(bool(self.content))
        self.hBoxLayout.addLayout(self.textLayout)

        # add widget layout
        if self.orient == Qt.Horizontal:
            self.hBoxLayout.addLayout(self.widgetLayout)
            self.widgetLayout.setSpacing(10)
        else:
            self.textLayout.addLayout(self.widgetLayout)

        self.widgetLayout.addStretch(1)
        self.addWidget(self.isKeyCheckBox)
        self.addWidget(self.isMouseCheckBox)
        self.addWidget(self.recordButton)
        self.addWidget(SplitLineWidget())

        self.addWidget(self.isLoopCheckBox)
        self.addWidget(self.playButton)

        # add close button to layout
        self.hBoxLayout.addSpacing(12)
        self.hBoxLayout.addWidget(self.closeButton, 0, Qt.AlignVCenter | Qt.AlignLeft)

    def __setQss(self):
        self.titleLabel.setObjectName('titleLabel')
        self.contentLabel.setObjectName('contentLabel')
        if isinstance(self.icon, Enum):
            self.setProperty('type', self.icon.value)
        self.setStyleSheet("""
            KeyMacroInfoBar {
                border: 1px solid rgb(229, 229, 229);
                border-radius: 6px;
                background-color: rgb(246, 246, 246);
            }

            KeyMacroInfoBar:focus {
                border: 1px solid rgb(219, 219, 219);
                border-radius: 6px;
                background-color: rgb(250, 250, 250);
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

    def __setContent(self, text: str):
        self.content = text

    def __recording(self, event):
        if event:
            self.playButton.setEnabled(False)
            self.recordButton.setIcon(FluentIcon.PAUSE)
            self.keyMacro.startRecording(isKey=self.isKeyCheckBox.isChecked(), isMouse=self.isMouseCheckBox.isChecked())
        else:
            self.playButton.setEnabled(True)
            self.recordButton.setIcon(FluentIcon.PLAY)
            self.keyMacro.stopRecording()

    def __recorded(self):
        self.__recording(False)
        self.recordButton.setChecked(False)
        self.recordedSignal.emit()

    def __playing(self, event):
        def callback():
            self.stoppedSignal.emit()

        if event:
            self.recordButton.setEnabled(False)
            self.playButton.setIcon(FluentIcon.PAUSE_BOLD)
            self.keyMacro.playRecord(isLoop=self.isLoopCheckBox.isChecked(), callback=callback)
        else:
            self.recordButton.setEnabled(True)
            self.playButton.setIcon(FluentIcon.PLAY_SOLID)
            self.keyMacro.terminateRecord()

    def __stopped(self):
        self.playButton.setChecked(False)
        self.playButton.setIcon(FluentIcon.PLAY_SOLID)
        self.recordButton.setEnabled(True)

    def addWidget(self, widget: QWidget, stretch=0):
        """ add widget to info bar """
        self.widgetLayout.addSpacing(10)
        align = Qt.AlignTop if self.orient == Qt.Vertical else Qt.AlignVCenter
        self.widgetLayout.addWidget(widget, stretch, Qt.AlignLeft | align)

    def closeEvent(self, e):
        idProperty = self.property("id")
        if idProperty:
            self.closedSignal.emit(idProperty)
        self.deleteLater()
        e.ignore()


class LabelEdit(LineEdit):
    def __init__(self, text: str = "", parent=None):
        super().__init__(parent=parent)
        self.setText(text)
        self.setReadOnly(True)
        self.setContentsMargins(0, 0, 0, 0)
        self.setMinimumWidth(100)
        self.setMaximumWidth(1000)

    def mouseDoubleClickEvent(self, event):
        self.setReadOnly(False)
        return super().mouseDoubleClickEvent(event)

    def focusOutEvent(self, event):
        self.setReadOnly(True)
        return super().focusOutEvent(event)


class SplitLineWidget(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.VLine)
        self.setStyleSheet("QFrame{background:#A0A0A0;min-height:5px;border:0px}")
        self.setFixedSize(2, 25)

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

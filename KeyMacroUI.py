import _thread
import time
import ujson

from enum import Enum
from pathlib import Path

from PyQt5.QtCore import pyqtSignal, Qt, QPropertyAnimation, QSize
from PyQt5.QtWidgets import QApplication, QWidget, QFrame, QLabel, QHBoxLayout, QVBoxLayout, QGraphicsOpacityEffect, QTableWidgetItem
from qfluentwidgets import MSFluentTitleBar, Icon, FluentIcon, TransparentToolButton, TransparentToggleToolButton, CheckBox, LineEdit, MessageBox, TableWidget, FlyoutView, \
    FlyoutAnimationType, Flyout
from qfluentwidgets.components.widgets.frameless_window import FramelessWindow
from qfluentwidgets.components.widgets.info_bar import InfoIconWidget

from KeyMacro import KeyMacro


class KeyMacroUI(FramelessWindow):

    def __init__(self):
        super().__init__()
        self.keyMacros: dict = {}
        self.keyMacroWidgets: dict = {}
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

        self.keyMacrosUI = self.__loadKeyMacrosUI()

        mainLayout = QVBoxLayout()
        mainLayout.addLayout(self.keyMacrosUI)
        self.setLayout(mainLayout)

    def __loadKeyMacrosUI(self):
        keyMacroLayout = QVBoxLayout()
        keyMacroLayout.setSpacing(10)
        for macroID, keyMacro in self.keyMacros.items():
            macroInfoBar = KeyMacroInfoBar(FluentIcon.QUICK_NOTE, keyMacro, parent=self)
            macroInfoBar.closedSignal.connect(self.__delKeyMacro)
            macroInfoBar.recordedSignal.connect(self.__updateKeyMacro)

            keyMacroLayout.addWidget(macroInfoBar)
            self.keyMacroWidgets[macroID] = macroInfoBar

        newInfoBar = KeyMacroInfoBar(FluentIcon.ADD_TO, {'title': "New", "name": "新建脚本"}, False, self)
        newInfoBar.closedSignal.connect(self.__delKeyMacro)
        newInfoBar.recordedSignal.connect(self.__updateKeyMacro)
        keyMacroLayout.addWidget(newInfoBar)
        self.keyMacroWidgets[newInfoBar.id] = newInfoBar
        return keyMacroLayout

    def __updateKeyMacro(self, macroID: str):
        if macroID not in self.keyMacros:
            keyMacroInfoBar = self.keyMacroWidgets[macroID]
            self.keyMacros[macroID] = keyMacroInfoBar.macroConfig

            newInfoBar = KeyMacroInfoBar(FluentIcon.ADD_TO, {'title': "New", "name": "新建脚本"}, False, self)
            newInfoBar.closedSignal.connect(self.__delKeyMacro)
            newInfoBar.recordedSignal.connect(self.__updateKeyMacro)
            self.keyMacrosUI.addWidget(newInfoBar)
            self.keyMacroWidgets[newInfoBar.id] = newInfoBar

        self.saveKeyMacros()

    def __delKeyMacro(self, macroID: str):
        if macroID in self.keyMacros:
            self.keyMacros.pop(macroID)
            self.saveKeyMacros()

    def loadKeyMacros(self):
        if self.macrosPath.exists():
            self.keyMacros = loadJson(self.macrosPath)

    def saveKeyMacros(self):
        dumpJson(self.macrosPath, self.keyMacros)

    def closeEvent(self, event):
        self.saveKeyMacros()


class KeyMacroInfoBar(QFrame):
    closedSignal = pyqtSignal(str)
    playedSignal = pyqtSignal(str)
    recordedSignal = pyqtSignal(str)

    def __init__(self, icon, macroConfig: dict,  isClosable=True, parent=None):
        super().__init__(parent=parent)
        self.icon = icon
        self.isClosable = isClosable

        self.macroConfig = macroConfig
        if "id" not in macroConfig:
            macroConfig['id'] = str(time.time_ns())
        self.id = macroConfig['id']
        self.keyMacro = KeyMacro(macroConfig.get("record"))

        self.__initUI()

    def __initUI(self):
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFixedHeight(75)
        self.playedSignal.connect(self.__played)
        self.recordedSignal.connect(self.__recorded)

        self.titleLabel = QLabel(self.macroConfig.get('title', ""))
        self.contentLabel = LabelEdit()
        self.contentLabel.setText(self.macroConfig.get('name', ""))
        self.contentLabel.textEdited.connect(self.__setName)
        self.closeButton = TransparentToolButton(FluentIcon.CLOSE)
        self.iconWidget = InfoIconWidget(self.icon)

        self.hBoxLayout = QHBoxLayout(self)
        self.textLayout = QHBoxLayout()
        self.widgetLayout = QHBoxLayout()

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

        self.editButton = TransparentToolButton(FluentIcon.EDIT)
        self.editButton.clicked.connect(self.__editing)

        self.isKeyCheckBox = CheckBox("键盘")
        self.isKeyCheckBox.setChecked(True)

        self.isMouseCheckBox = CheckBox("鼠标")
        self.isMouseCheckBox.setChecked(True)

        self.isLoopCheckBox = CheckBox("循环")

        self.closeButton.setFixedSize(36, 36)
        self.closeButton.setIconSize(QSize(12, 12))
        self.closeButton.setCursor(Qt.PointingHandCursor)
        self.closeButton.setEnabled(self.isClosable)
        self.closeButton.clicked.connect(self.__fadeOut)

        self.__setQss()
        self.__initLayout()

    def __initLayout(self):
        self.hBoxLayout.setContentsMargins(6, 6, 6, 6)
        self.hBoxLayout.setSpacing(0)

        self.textLayout.setAlignment(Qt.AlignVCenter)
        self.textLayout.setContentsMargins(1, 8, 0, 8)
        self.textLayout.setSpacing(5)

        # add icon to layout
        self.hBoxLayout.addWidget(self.iconWidget, 0, Qt.AlignVCenter | Qt.AlignLeft)

        # add title to layout
        self.textLayout.addWidget(self.titleLabel, 0, Qt.AlignVCenter | Qt.AlignLeft)
        self.textLayout.addSpacing(7)
        self.titleLabel.setVisible(bool(self.macroConfig.get('title')))

        self.textLayout.addWidget(self.contentLabel, 0, Qt.AlignVCenter | Qt.AlignLeft)
        self.contentLabel.setVisible(bool(self.macroConfig.get('name')))
        self.hBoxLayout.addLayout(self.textLayout)

        self.hBoxLayout.addLayout(self.widgetLayout)

        self.widgetLayout.addStretch(1)
        self.addWidget(self.isKeyCheckBox)
        self.addWidget(self.isMouseCheckBox)
        self.addWidget(self.recordButton)
        self.addWidget(self.editButton)
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
        if not showMessageDialog("提示", "是否删除脚本?", self):
            return
        self.opacityAni.setDuration(100)
        self.opacityAni.setStartValue(1)
        self.opacityAni.setEndValue(0)
        self.opacityAni.finished.connect(self.close)
        self.opacityAni.start()

    def __setName(self, text: str):
        self.macroConfig['name'] = text

    def __recording(self, event):
        def record():
            self.recordedSignal.emit(self.id)

        if event:
            if len(self.keyMacro.eventsRecord) > 0 and not showMessageDialog("提示", "是否要重新录制脚本?", self):
                self.recordButton.setChecked(False)
                return
            self.keyMacro.terminateRecord()
            self.playButton.setEnabled(False)
            self.recordButton.setIcon(FluentIcon.PAUSE)
            if not self.recordButton.isChecked():
                self.recordButton.setChecked(True)
            self.keyMacro.startRecording(isKey=self.isKeyCheckBox.isChecked(), isMouse=self.isMouseCheckBox.isChecked())
        else:
            self.keyMacro.stopRecording()
            if len(self.keyMacro.eventsRecord) > 0:
                self.playButton.setEnabled(True)
            self.recordButton.setIcon(FluentIcon.PLAY)
            if self.recordButton.isChecked():
                self.recordButton.setChecked(False)
            _thread.start_new_thread(record, ())

    def __recorded(self, _id):
        if len(self.keyMacro.eventsRecord) > 0:
            self.macroConfig['title'] = "Script"
            self.macroConfig['record'] = self.keyMacro.eventsRecord
            self.titleLabel.setText("Script")
            self.icon = FluentIcon.QUICK_NOTE
            self.iconWidget.icon = self.icon
            self.closeButton.setEnabled(True)

    def __playing(self, event):
        def callback():
            self.playedSignal.emit(self.id)

        if event:
            print("playing...")
            self.recordButton.setEnabled(False)
            self.playButton.setIcon(FluentIcon.PAUSE_BOLD)
            if not self.playButton.isChecked():
                self.playButton.setChecked(True)
            self.keyMacro.playRecord(isLoop=self.isLoopCheckBox.isChecked(), callback=callback)
        else:
            print('stop playing.')
            self.keyMacro.terminateRecord()
            self.recordButton.setEnabled(True)
            self.playButton.setIcon(FluentIcon.PLAY_SOLID)
            if self.playButton.isChecked():
                self.playButton.setChecked(False)

    def __played(self, _id):
        self.playButton.setChecked(False)
        self.playButton.setIcon(FluentIcon.PLAY_SOLID)
        self.recordButton.setEnabled(True)

    def __editing(self, event):
        view = FlyoutView(self.tr('编辑'), "")

        tableFrame = TableFrame()
        tableFrame.setMinimumSize(370, 250)
        sheet = []
        lastTime = next(iter(self.keyMacro.eventsRecord[0].values()))['time'] if len(self.keyMacro.eventsRecord) > 0 else 0
        for record in self.keyMacro.eventsRecord:
            row = []
            for values in record.values():
                for k, v in values.items():
                    if k == "time":
                        row.append(format(v - lastTime, '.9f'))
                        lastTime = v
                    else:
                        row.append(v)
            sheet.append(row)

        tableFrame.setSheet(sheet, ("键位", "动作", "时长(秒)"))
        view.addWidget(tableFrame, align=Qt.AlignCenter)

        Flyout.make(view, self.editButton, self.window(), FlyoutAnimationType.DROP_DOWN)

    def addWidget(self, widget: QWidget, stretch=0):
        self.widgetLayout.addSpacing(15)
        self.widgetLayout.addWidget(widget, stretch, Qt.AlignLeft | Qt.AlignVCenter)

    def addLayout(self, layout, stretch=0):
        self.widgetLayout.addSpacing(15)
        self.widgetLayout.addLayout(layout, stretch)

    def closeEvent(self, e):
        self.closedSignal.emit(self.id)
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


class TableFrame(TableWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.__initUI()

    def __initUI(self):
        self.setBorderRadius(8)
        self.setBorderVisible(True)

    def setSheet(self, sheet: list | tuple, horHeader: list | tuple = None, verHeader: list | tuple = None):
        self.clear()
        row = len(sheet)
        column = len(sheet[0]) if row > 0 else 0
        self.setColumnCount(column)
        self.setRowCount(row)

        if horHeader is None:
            self.horizontalHeader().hide()
        else:
            self.setHorizontalHeaderLabels(horHeader)
        if verHeader is None:
            self.verticalHeader().hide()
        else:
            self.setVerticalHeaderLabels(verHeader)

        for i, items in enumerate(sheet):
            for j, item in enumerate(items):
                self.setItem(i, j, QTableWidgetItem(str(item)))
        self.resizeColumnsToContents()


class SplitLineWidget(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.VLine)
        self.setStyleSheet("QFrame{background:#A0A0A0;min-height:5px;border:0px}")
        self.setFixedSize(2, 25)

# ------------------------------------------Common------------------------------------------ #


def showMessageDialog(title: str, content: str, parent: QWidget):
    if parent.window():
        title = parent.tr(title)
        content = parent.tr(content)
        w = MessageBox(title, content, parent.window())
        # w.setContentCopyable(True)
        if w.exec():
            return True
    return False


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

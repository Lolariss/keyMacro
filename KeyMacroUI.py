import _thread
import time

import ujson

from enum import Enum
from pathlib import Path

from PyQt5.QtCore import pyqtSignal, Qt, QPropertyAnimation
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtWidgets import QApplication, QWidget, QFrame, QLabel, QHBoxLayout, QVBoxLayout, QGraphicsOpacityEffect
from qfluentwidgets import MSFluentTitleBar, Icon, FluentIcon, TransparentToolButton, TransparentToggleToolButton, CheckBox, LineEdit, MessageBox, FlyoutView, \
    FlyoutAnimationType, Flyout, ScrollArea, PushButton, SpinBox, TextEdit
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
        self.setTitleBar(MSFluentTitleBar(self))
        self.setWindowTitle("按按又键键(￣▽￣)")
        self.setWindowIcon(Icon(FluentIcon.FINGERPRINT))
        self.resize(700, 250)
        self.setMaximumSize(1920, 1080)
        self.setMinimumSize(700, 250)
        self.setFocusPolicy(Qt.StrongFocus)

        self.keyMacrosUI = self.__loadKeyMacrosUI()
        keyMacrosBg = BackgroundWidget()
        keyMacrosBg.setLayout(self.keyMacrosUI)

        keyMacrosArea = ScrollArea()
        keyMacrosArea.setWidgetResizable(True)
        keyMacrosArea.setWidget(keyMacrosBg)
        keyMacrosArea.setObjectName("keyMacrosArea")
        keyMacrosArea.setStyleSheet("""#keyMacrosArea{border: 0px ;}""")

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(keyMacrosArea)
        self.setLayout(mainLayout)

    def __newKeyMacroInfoBar(self):
        macroConfig = {
            "id": str(time.time_ns()),
            'title': "New",
            "name": "新建脚本"
        }
        keyMacroInfoBar = KeyMacroInfoBar(FluentIcon.ADD_TO, macroConfig)
        keyMacroInfoBar.closedSignal.connect(self.__delKeyMacro)
        keyMacroInfoBar.recordedSignal.connect(self.__updateKeyMacro)
        self.keyMacroWidgets[keyMacroInfoBar.id] = keyMacroInfoBar
        return keyMacroInfoBar

    def __loadKeyMacrosUI(self):
        keyMacroLayout = QVBoxLayout()
        keyMacroLayout.setSpacing(10)
        for macroID, keyMacro in self.keyMacros.items():
            macroInfoBar = KeyMacroInfoBar(FluentIcon.QUICK_NOTE, keyMacro)
            macroInfoBar.closedSignal.connect(self.__delKeyMacro)
            macroInfoBar.recordedSignal.connect(self.__updateKeyMacro)

            keyMacroLayout.addWidget(macroInfoBar)
            self.keyMacroWidgets[macroID] = macroInfoBar

        newInfoBar = self.__newKeyMacroInfoBar()
        keyMacroLayout.addWidget(newInfoBar)
        if len(self.keyMacros) > 2:
            self.resize(self.width(), min(len(self.keyMacros) * 75, 500))
        return keyMacroLayout

    def __updateKeyMacro(self, macroID: str):
        if macroID not in self.keyMacros:
            keyMacroInfoBar = self.keyMacroWidgets[macroID]
            self.keyMacros[macroID] = keyMacroInfoBar.macroConfig

            newInfoBar = self.__newKeyMacroInfoBar()
            if self.height() < 500:
                self.resize(self.width(), self.height() + 75)
            self.keyMacrosUI.addWidget(newInfoBar)

    def __delKeyMacro(self, macroID: str):
        if macroID in self.keyMacros:
            self.keyMacros.pop(macroID)

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

    def __init__(self, icon, macroConfig: dict, parent=None):
        super().__init__(parent=parent)
        self.icon = icon

        self.macroConfig = macroConfig
        self.id = macroConfig.get("id")
        self.keyMacro = KeyMacro(macroConfig.get("record"))

        self.__initUI()

    def __initUI(self):
        self.playedSignal.connect(self.__played)
        self.recordedSignal.connect(self.__recorded)
        self.setFixedHeight(75)
        self.setFocusPolicy(Qt.StrongFocus)

        self.titleLabel = QLabel(self.macroConfig.get('title', ""))
        self.contentLabel = LabelEdit()
        self.contentLabel.setText(self.macroConfig.get('name', ""))
        self.contentLabel.textEdited.connect(self.__setName)
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

        self.isKeyCheckBox = CheckBox("键盘")
        self.isKeyCheckBox.setChecked(True)

        self.isMouseCheckBox = CheckBox("鼠标")
        self.isMouseCheckBox.setChecked(True)

        self.isLoopCheckBox = CheckBox("循环")

        self.editButton = TransparentToolButton(FluentIcon.EDIT)
        self.editButton.clicked.connect(self.__editing)

        self.settingButton = TransparentToolButton(FluentIcon.SETTING)
        self.settingButton.clicked.connect(self.__setting)

        self.editingView = EditScriptView('编辑')
        self.editingView.submitSignal.connect(self.__setRecord)

        self.settingView = SettingsView("设置")
        self.settingView.setDelayValue(self.macroConfig.get("delay", 0))
        self.settingView.removeSignal.connect(self.__fadeOut)
        self.settingView.delayChangedSignal.connect(self.__setDelay)

        if len(self.keyMacro.eventsRecord) <= 0:
            self.playButton.setEnabled(False)
            self.settingButton.setEnabled(False)

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

        # # add title to layout
        self.textLayout.addWidget(self.titleLabel, 0, Qt.AlignVCenter | Qt.AlignLeft)
        self.textLayout.addSpacing(7)
        if not self.macroConfig.get('title'):
            self.titleLabel.setVisible(False)

        self.textLayout.addWidget(self.contentLabel, 0, Qt.AlignVCenter | Qt.AlignLeft)
        if not self.macroConfig.get('name'):
            self.contentLabel.setVisible(False)

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
        self.hBoxLayout.addWidget(self.settingButton, 0, Qt.AlignVCenter | Qt.AlignLeft)

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

    def __setDelay(self, delay: int):
        self.macroConfig['delay'] = delay

    def __setRecord(self, text: str):
        pass

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
            self.settingButton.setEnabled(True)

    def __playing(self, event):
        def callback():
            self.playedSignal.emit(self.id)

        if event:
            print("playing...")
            self.recordButton.setEnabled(False)
            self.playButton.setIcon(FluentIcon.PAUSE_BOLD)
            self.isLoopCheckBox.setEnabled(False)
            self.editButton.setEnabled(False)
            if not self.playButton.isChecked():
                self.playButton.setChecked(True)
            self.keyMacro.playRecord(True, self.isLoopCheckBox.isChecked(), self.macroConfig.get('delay'), callback)
        else:
            print('stop playing.')
            self.keyMacro.terminateRecord()
            self.recordButton.setEnabled(True)
            self.playButton.setIcon(FluentIcon.PLAY_SOLID)
            if self.playButton.isChecked():
                self.playButton.setChecked(False)
            self.isLoopCheckBox.setEnabled(True)
            self.editButton.setEnabled(True)

    def __played(self, _id):
        self.playButton.setChecked(False)
        self.playButton.setIcon(FluentIcon.PLAY_SOLID)
        self.recordButton.setEnabled(True)
        self.isLoopCheckBox.setEnabled(True)
        self.editButton.setEnabled(True)

    def __editing(self, event):
        contents = ""
        lastTime = next(iter(self.keyMacro.eventsRecord[0].values()))['time'] if len(self.keyMacro.eventsRecord) > 0 else 0
        for record in self.keyMacro.eventsRecord:
            line = ""
            for values in record.values():
                for k, v in values.items():
                    if k == "time":
                        line += f"{int((v - lastTime) * 1000):04d}"
                        lastTime = v
                    else:
                        line += f"{str(v).strip()}, "
            contents += f"{line}\n"

        self.editingView.setEditText(contents)
        Flyout.make(self.editingView, self.editButton, self.window(), FlyoutAnimationType.DROP_DOWN, False)

    def __setting(self, event):
        Flyout.make(self.settingView, self.settingButton, self.window(), FlyoutAnimationType.DROP_DOWN, False)

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


class EditScriptView(FlyoutView):
    submitSignal = pyqtSignal(str)

    def __init__(self, title: str, parent=None):
        super().__init__(title, "", parent=parent)
        self.__initUI()

    def __initUI(self):
        self.editText = TextEdit()
        self.editText.setMinimumSize(250, 200)

        self.submitButton = PushButton(FluentIcon.SAVE, "保存")
        self.submitButton.clicked.connect(self.__submit)

        self.addWidget(self.editText)
        self.addWidget(self.submitButton, Qt.AlignRight)

    def __submit(self, event):
        self.submitSignal.emit(self.editText.toPlainText())

    def setEditText(self, text: str):
        self.editText.setText(text)


class SettingsView(FlyoutView):
    removeSignal = pyqtSignal()
    delayChangedSignal = pyqtSignal(int)

    def __init__(self, title: str, parent=None):
        super().__init__(title, "", parent=parent)
        self.__initUI()

    def __initUI(self):
        self.removeButton = PushButton(FluentIcon.DELETE, "删除脚本")
        self.removeButton.setCursor(Qt.PointingHandCursor)
        self.removeButton.clicked.connect(self.removeSignal)

        self.delayEdit = SpinBox()
        self.delayEdit.setMinimum(0)
        self.delayEdit.setMaximum(2147483647)
        self.delayEdit.setSingleStep(1000)
        self.delayEdit.valueChanged.connect(self.delayChangedSignal)
        self.delayLabel = QLabel("循环间隔/ms")
        self.delayLabel.setStyleSheet("font: 14px 'Segoe UI', 'Microsoft YaHei', 'PingFang SC';")

        self.addWidget(self.removeButton)

        self.widgetLayout.addSpacing(5)
        self.addWidget(self.delayLabel)
        self.addWidget(self.delayEdit)

    def getDelayValue(self):
        return self.delayEdit.value()

    def setDelayValue(self, value):
        self.delayEdit.setValue(value)


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


class BackgroundWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QPen(QColor(200, 200, 200), 0.5, Qt.DotLine))

        # 绘制水平网格线
        for y in range(0, self.height(), 10):  # 20为网格间距
            painter.drawLine(0, y, self.width(), y)

        # 绘制垂直网格线
        for x in range(0, self.width(), 10):
            painter.drawLine(x, 0, x, self.height())


class SplitLineWidget(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)
        self.setStyleSheet("QFrame{background:#A0A0A0;min-height:5px;border:0px}")
        self.setFixedSize(2, 25)

# ------------------------------------------Common------------------------------------------ #


def showMessageDialog(title: str, content: str, parent: QWidget):
    if parent.window():
        title = parent.tr(title)
        content = parent.tr(content)
        msgBox = MessageBox(title, content, parent.window())
        msgBox.yesButton.setText("确定")
        msgBox.cancelButton.setText("取消")
        # w.setContentCopyable(True)
        if msgBox.exec():
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
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    window = KeyMacroUI()
    window.show()
    sys.exit(app.exec_())

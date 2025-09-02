import time
import winsound
import keyboard
import ujson
import _thread

from enum import Enum
from pathlib import Path
from KeyMacro import KeyMacro
from utils import loadJson, dumpJson, logger

from PyQt5.QtCore import pyqtSignal, Qt, QPropertyAnimation, pyqtSlot
from PyQt5.QtGui import QPainter, QColor, QPen, QKeySequence
from PyQt5.QtWidgets import QApplication, QWidget, QFrame, QLabel, QHBoxLayout, QVBoxLayout, QGraphicsOpacityEffect
from qfluentwidgets import MSFluentTitleBar, Icon, FluentIcon, TransparentToolButton, TransparentToggleToolButton, CheckBox, LineEdit, MessageBox, FlyoutView, \
    FlyoutAnimationType, Flyout, ScrollArea, PushButton, SpinBox, TextEdit, setFont
from qfluentwidgets.components.widgets.frameless_window import FramelessWindow
from qfluentwidgets.components.widgets.info_bar import InfoIconWidget, InfoBar, InfoBarPosition


SOUND_DIR = Path.cwd() / "sound"


class KeyMacroUI(FramelessWindow):

    def __init__(self):
        super().__init__()
        self.keyMacros: dict = {}
        self.keyMacroWidgets: dict = {}
        self.macrosPath = Path.cwd() / "keyMacros.json"
        self.loadKeyMacros()

        self.currentInfoBar = None
        self.currentNewInfoBar = None
        self.__initUI()

        keyboard.add_hotkey("ctrl+alt+f9", self.__shortCutRecord, suppress=True)
        keyboard.add_hotkey("ctrl+alt+f10", self.__shortCutPlay, suppress=True)

    def __initUI(self):
        self.setContentsMargins(0, 35, 0, 10)
        self.setTitleBar(MSFluentTitleBar(self))
        self.setWindowTitle("按按又键键(￣▽￣)")
        self.setWindowIcon(Icon(FluentIcon.FINGERPRINT))
        self.resize(700, 200)
        self.setMaximumSize(1920, 1080)
        self.setMinimumSize(700, 200)
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
        keyMacroInfoBar.deletedSignal.connect(self.__deleteKeyMacro)
        keyMacroInfoBar.recordedSignal.connect(self.__updateKeyMacro)
        keyMacroInfoBar.clickedSignal.connect(self.__clickKeyMacro)
        self.keyMacroWidgets[keyMacroInfoBar.id] = keyMacroInfoBar
        self.currentNewInfoBar = keyMacroInfoBar
        return keyMacroInfoBar

    def __loadKeyMacrosUI(self):
        keyMacroLayout = QVBoxLayout()
        keyMacroLayout.setSpacing(10)
        for macroID, keyMacro in self.keyMacros.items():
            macroInfoBar = KeyMacroInfoBar(FluentIcon.QUICK_NOTE, keyMacro)
            macroInfoBar.deletedSignal.connect(self.__deleteKeyMacro)
            macroInfoBar.recordedSignal.connect(self.__updateKeyMacro)
            macroInfoBar.clickedSignal.connect(self.__clickKeyMacro)
            keyMacroLayout.addWidget(macroInfoBar)
            self.keyMacroWidgets[macroID] = macroInfoBar

        newInfoBar = self.__newKeyMacroInfoBar()
        keyMacroLayout.addWidget(newInfoBar)
        if len(self.keyMacros) > 0:
            self.resize(self.width(), self.height() + min(len(self.keyMacros) * 75, 500))
        return keyMacroLayout

    def __updateKeyMacro(self, macroID: str):
        if macroID not in self.keyMacros:
            keyMacroInfoBar = self.keyMacroWidgets[macroID]
            if len(keyMacroInfoBar.keyMacro.eventsRecord) <= 0:
                return
            self.keyMacros[macroID] = keyMacroInfoBar.macroConfig

            newInfoBar = self.__newKeyMacroInfoBar()
            if self.height() < 500:
                self.resize(self.width(), self.height() + 75)
            newInfoBar.setOpacity(0)
            self.keyMacrosUI.addWidget(newInfoBar)
            newInfoBar.fadeIn()
            self.update()

    def __deleteKeyMacro(self, macroID: str):
        if macroID in self.keyMacros:
            self.keyMacros.pop(macroID)

    def __clickKeyMacro(self, macroID: str):
        if macroID in self.keyMacros:
            self.currentInfoBar = self.keyMacroWidgets.get(macroID)

    def __shortCutPlay(self):
        if self.currentInfoBar is not None:
            logger.info("shortcut play...")
            self.currentInfoBar.playing(not self.currentInfoBar.playButton.isChecked())

    def __shortCutRecord(self):
        if self.currentNewInfoBar is not None:
            logger.info("shortcut record...")
            self.currentNewInfoBar.recording(not self.currentNewInfoBar.recordButton.isChecked())

    def loadKeyMacros(self):
        if self.macrosPath.exists():
            self.keyMacros = loadJson(self.macrosPath)

    def saveKeyMacros(self):
        dumpJson(self.macrosPath, self.keyMacros)

    def closeEvent(self, event):
        self.saveKeyMacros()
        keyboard.remove_all_hotkeys()
        event.accept()


class KeyMacroInfoBar(QFrame):
    clickedSignal = pyqtSignal(str)
    deletedSignal = pyqtSignal(str)
    playedSignal = pyqtSignal(str)
    recordedSignal = pyqtSignal(str)

    def __init__(self, icon, macroConfig: dict, parent=None):
        super().__init__(parent=parent)
        self.macroConfig = macroConfig
        self.id = macroConfig.get("id")
        self.keyMacro = KeyMacro(macroConfig.get("record"))
        self.hotkey = None

        self.icon = icon
        self.flyoutHandler = None

        self.__initUI()
        self.setHotkey(macroConfig.get('hotkey', ""))

    def __initUI(self):
        self.playedSignal.connect(self.__played)
        self.recordedSignal.connect(self.__recorded)
        self.setFixedHeight(75)
        self.setFocusPolicy(Qt.StrongFocus)

        self.titleLabel = QLabel(self.macroConfig.get('title', ""))
        self.contentLabel = LabelEdit()
        self.contentLabel.setText(self.macroConfig.get('name', ""))
        self.contentLabel.textEdited.connect(self.setName)
        self.iconWidget = InfoIconWidget(self.icon)

        self.hBoxLayout = QHBoxLayout(self)
        self.textLayout = QHBoxLayout()
        self.widgetLayout = QHBoxLayout()

        self.opacityEffect = QGraphicsOpacityEffect(self)
        self.opacityAni = QPropertyAnimation(self.opacityEffect, b'opacity', self)
        self.opacityEffect.setOpacity(1)
        self.setGraphicsEffect(self.opacityEffect)

        self.recordButton = TransparentToggleToolButton(FluentIcon.PLAY)
        self.recordButton.clicked.connect(self.recording)
        self.recordButton.setToolTip("开始录制")

        self.playButton = TransparentToggleToolButton(FluentIcon.PLAY_SOLID)
        self.playButton.clicked.connect(self.playing)
        self.playButton.setToolTip("开始播放")

        self.isKeyCheckBox = CheckBox("键盘")
        self.isKeyCheckBox.setChecked(True)

        self.isMouseCheckBox = CheckBox("鼠标")
        self.isMouseCheckBox.setChecked(True)

        self.isLoopCheckBox = CheckBox("循环")

        self.editButton = TransparentToolButton(FluentIcon.EDIT)
        self.editButton.clicked.connect(self.__editing)
        self.editButton.setToolTip("编辑脚本")

        self.settingButton = TransparentToolButton(FluentIcon.SETTING)
        self.settingButton.clicked.connect(self.__setting)
        self.settingButton.setToolTip("设置")

        self.editingView = EditScriptView('编辑')
        self.editingView.submitSignal.connect(self.setRecord)

        self.settingView = SettingsView("设置")
        self.settingView.setDelayValue(self.macroConfig.get("delay", 0))
        self.settingView.setHotKey(self.macroConfig.get("hotkey", ""))
        self.settingView.removeSignal.connect(self.__deleting)
        self.settingView.delayChangedSignal.connect(self.setDelay)
        self.settingView.hotkeyChangedSignal.connect(self.setHotkey)

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
        self.textLayout.setSpacing(10)

        self.hBoxLayout.addWidget(self.iconWidget, alignment=Qt.AlignVCenter | Qt.AlignLeft)

        if not self.macroConfig.get('title'):
            self.titleLabel.setVisible(False)
        if not self.macroConfig.get('name'):
            self.contentLabel.setVisible(False)
        self.textLayout.addWidget(self.titleLabel, alignment=Qt.AlignVCenter | Qt.AlignLeft)
        self.textLayout.addWidget(self.contentLabel)

        self.hBoxLayout.addLayout(self.textLayout)
        self.hBoxLayout.addLayout(self.widgetLayout)

        self.addWidget(self.isKeyCheckBox)
        self.addWidget(self.isMouseCheckBox)
        self.addWidget(self.recordButton)
        self.addWidget(self.editButton)
        self.addWidget(SplitLineWidget())

        self.addWidget(self.isLoopCheckBox)
        self.addWidget(self.playButton)

        # add close button to layout
        self.hBoxLayout.addSpacing(12)
        self.hBoxLayout.addWidget(self.settingButton, alignment=Qt.AlignVCenter | Qt.AlignRight)

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

    def setName(self, text: str):
        self.macroConfig['name'] = text

    def setDelay(self, delay: int):
        self.macroConfig['delay'] = delay

    def setHotkey(self, hotkey: str = ""):
        if self.hotkey is not None:
            keyboard.remove_hotkey(self.hotkey)

        self.macroConfig['hotkey'] = hotkey
        if len(hotkey) > 0:
            logger.info(f'set {hotkey} {self.macroConfig.get("name", "")} shortcut play')
            self.hotkey = keyboard.add_hotkey(hotkey, self.playing)
        else:
            logger.info(f'clear {self.macroConfig.get("name", "")} shortcut play')

    def setRecord(self, contents: str):
        def recorded():
            self.recordedSignal.emit(self.id)

        if len(contents) > 0:
            keyMacro = KeyMacro()
            row, delay = 0, 0
            try:
                for row, line in enumerate(contents.splitlines()):
                    if len(line.strip()) == 0:
                        continue
                    if ':' in line:
                        lineSplit = line.split(":")
                        recordKey, recordType = lineSplit[0].strip(), lineSplit[1].strip()
                        if recordType == "move":
                            keyMacro.addMouseRecord(ujson.loads(recordKey), recordType, delay)
                        elif recordType == "wheel":
                            keyMacro.addMouseRecord(float(recordKey), recordType, delay)
                        elif recordKey in {"mouse left", "mouse right", "mouse middle"}:
                            keyMacro.addMouseRecord(recordKey.replace("mouse ", ''), recordType, delay)
                        else:
                            keyMacro.addKeyRecord(recordKey, recordType, delay)
                        delay = 0
                    else:
                        delay = float(line.strip())
                self.keyMacro = keyMacro
            except Exception as e:
                logger.exception(e)
                InfoBar.error("", f"保存失败!第{row + 1}行发现错误!", Qt.Horizontal, True, 5000, InfoBarPosition.TOP_LEFT, self.window())
                return

            self.clearFlyout()
            self.switchRecordStatus(True)
            _thread.start_new_thread(recorded, ())
            InfoBar.info("", "保存成功!", Qt.Horizontal, True, 2000, InfoBarPosition.TOP_LEFT, self.window())
        else:
            InfoBar.warning("", "脚本内容不能为空!", Qt.Horizontal, True, 2000, InfoBarPosition.TOP_LEFT, self.window())

    def recording(self, enable: bool):
        def recorded():
            self.recordedSignal.emit(self.id)

        if enable:
            if len(self.keyMacro.eventsRecord) > 0 and not showMessageDialog("提示", "是否要重新录制脚本?", self):
                self.recordButton.setChecked(False)
                return
            self.keyMacro.terminateRecord()
            winsound.PlaySound(str(SOUND_DIR / "recordOn.wav"), winsound.SND_FILENAME | winsound.SND_ASYNC)
            self.switchRecordStatus(False)
            self.keyMacro.startRecording(self.isKeyCheckBox.isChecked(), self.isMouseCheckBox.isChecked())
        else:
            self.keyMacro.stopRecording(self.isKeyCheckBox.isChecked(), self.isMouseCheckBox.isChecked())
            winsound.PlaySound(str(SOUND_DIR / "recordOff.wav"), winsound.SND_FILENAME | winsound.SND_ASYNC)
            self.switchRecordStatus(True)
            _thread.start_new_thread(recorded, ())

    @pyqtSlot()
    def __recorded(self):
        if len(self.keyMacro.eventsRecord) > 0:
            self.macroConfig['title'] = "Script"
            self.macroConfig['record'] = self.keyMacro.eventsRecord
            self.titleLabel.setText("Script")
            self.icon = FluentIcon.QUICK_NOTE
            self.iconWidget.icon = self.icon

    def playing(self, enable: bool = None):
        def callback():
            self.playedSignal.emit(self.id)

        if enable is None:
            enable = not self.playButton.isChecked()

        if enable:
            logger.info("playing...")
            winsound.PlaySound(str(SOUND_DIR / "playOn.wav"), winsound.SND_FILENAME | winsound.SND_ASYNC)
            self.switchPlayStatus(False)
            self.keyMacro.playRecord(True, self.isLoopCheckBox.isChecked(), self.macroConfig.get('delay', 0), callback)
        else:
            logger.info('stop playing.')
            self.keyMacro.terminateRecord(False)
            self.switchPlayStatus(True)
            winsound.PlaySound(str(SOUND_DIR / "playOff.wav"), winsound.SND_FILENAME | winsound.SND_ASYNC)

    @pyqtSlot()
    def __played(self):
        logger.info("play over.")
        winsound.PlaySound(str(SOUND_DIR / "playOff.wav"), winsound.SND_FILENAME | winsound.SND_ASYNC)
        self.switchPlayStatus(True)

    def __deleting(self):
        self.clearFlyout()
        if not showMessageDialog("提示", "是否删除脚本?", self):
            return
        self.fadeOut()
        self.deletedSignal.emit(self.id)

    def __editing(self, event):
        contents = ""
        lastTime = next(iter(self.keyMacro.eventsRecord[0].values()))['time'] if len(self.keyMacro.eventsRecord) > 0 else 0
        try:
            for eventRecord in self.keyMacro.eventsRecord:
                for eventType, record in eventRecord.items():
                    recordKey = record['key' if "key" in record else ('offset' if 'offset' in record else "delta")]
                    recordType = record['type']
                    recordTime = record['time']
                    if eventType == "mouse" and (recordKey == "left" or recordKey == "right" or recordKey == "middle"):
                        recordKey = f"mouse {recordKey}"

                    contents += f"{int((recordTime - lastTime) * 1000):04d}\n{recordKey}: {recordType}\n"
                    lastTime = recordTime
        except Exception as e:
            logger.exception(e)
            InfoBar.error("", "脚本文本化失败!", Qt.Horizontal, True, 5000, InfoBarPosition.TOP_LEFT, self.window())

        self.editingView.setEditText(contents)
        self.flyoutHandler = Flyout.make(self.editingView, self.editButton, self.window(), FlyoutAnimationType.DROP_DOWN, False)

    def __setting(self, event):
        self.flyoutHandler = Flyout.make(self.settingView, self.settingButton, self.window(), FlyoutAnimationType.DROP_DOWN, False)

    def addWidget(self, widget: QWidget, stretch=0):
        self.widgetLayout.addSpacing(15)
        self.widgetLayout.addWidget(widget, stretch, Qt.AlignLeft | Qt.AlignVCenter)

    def addLayout(self, layout, stretch=0):
        self.widgetLayout.addSpacing(15)
        self.widgetLayout.addLayout(layout, stretch)

    def fadeOut(self):
        self.opacityAni.setDuration(100)
        self.opacityAni.setStartValue(1)
        self.opacityAni.setEndValue(0)
        self.opacityAni.finished.connect(self.close)
        self.opacityAni.start()

    def fadeIn(self):
        self.opacityAni.setDuration(100)
        self.opacityAni.setStartValue(0)
        self.opacityAni.setEndValue(1)
        self.opacityAni.start()

    def clearFlyout(self):
        if self.flyoutHandler is not None:
            self.flyoutHandler.close()

    def switchRecordStatus(self, status: bool):
        self.recordButton.setChecked(not status)
        if status:
            self.recordButton.setIcon(FluentIcon.PLAY)
            if len(self.keyMacro.eventsRecord) > 0:
                self.playButton.setEnabled(status)
                self.settingButton.setEnabled(status)
        else:
            self.recordButton.setIcon(FluentIcon.PAUSE)
            self.playButton.setEnabled(status)
            self.settingButton.setEnabled(status)
        self.isKeyCheckBox.setEnabled(status)
        self.isMouseCheckBox.setEnabled(status)
        self.editButton.setEnabled(status)

    def switchPlayStatus(self, status: bool):
        self.playButton.setChecked(not status)
        if status:
            self.playButton.setIcon(FluentIcon.PLAY_SOLID)
        else:
            self.playButton.setIcon(FluentIcon.PAUSE_BOLD)
        self.recordButton.setEnabled(status)
        self.isLoopCheckBox.setEnabled(status)
        self.editButton.setEnabled(status)
        self.settingButton.setEnabled(status)

    def setOpacity(self, value: float):
        self.opacityEffect.setOpacity(value)

    def mousePressEvent(self, event):
        self.clickedSignal.emit(self.id)
        return super().mousePressEvent(event)

    def closeEvent(self, e):
        self.deleteLater()
        e.accept()


class EditScriptView(FlyoutView):
    submitSignal = pyqtSignal(str)

    def __init__(self, title: str, parent=None):
        super().__init__(title, "", parent=parent)
        self.__initUI()

    def __initUI(self):
        self.editText = TextEdit()
        self.editText.setMinimumSize(250, 200)
        setFont(self.editText, 16)

        self.submitButton = PushButton(FluentIcon.SAVE, "保存")
        self.submitButton.clicked.connect(self.__submit)

        self.addWidget(self.editText)
        self.addWidget(self.submitButton, align=Qt.AlignRight)

    def __submit(self, event):
        self.submitSignal.emit(self.editText.toPlainText())

    def setEditText(self, text: str):
        self.editText.setText(text)


class SettingsView(FlyoutView):
    removeSignal = pyqtSignal()
    delayChangedSignal = pyqtSignal(int)
    hotkeyChangedSignal = pyqtSignal(str)

    def __init__(self, title: str, parent=None):
        super().__init__(title, "", parent=parent)
        self.__initUI()

    def __initUI(self):
        self.setFocusPolicy(Qt.StrongFocus)

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

        self.hotkeyLabel = QLabel("快捷按键")
        self.hotkeyLabel.setStyleSheet("font: 14px 'Segoe UI', 'Microsoft YaHei', 'PingFang SC';")
        self.hotkeyEdit = HotKeyEdit()
        self.hotkeyEdit.textChanged.connect(self.hotkeyChangedSignal)

        self.addWidget(self.removeButton)

        self.widgetLayout.addSpacing(5)
        self.addWidget(self.delayLabel)
        self.addWidget(self.delayEdit)
        self.widgetLayout.addSpacing(5)
        self.addWidget(self.hotkeyLabel)
        self.addWidget(self.hotkeyEdit)

    def getDelayValue(self):
        return self.delayEdit.value()

    def setDelayValue(self, value):
        self.delayEdit.setValue(value)

    def getHotkey(self):
        return self.hotkeyEdit.text()

    def setHotKey(self, hotkey: str):
        self.hotkeyEdit.setText(hotkey)


class HotKeyEdit(LineEdit):

    def __init__(self, shortcut: str = "", parent=None):
        super().__init__(parent=parent)
        self.shortcut = shortcut
        self.__initUI()

    def __initUI(self):
        self.setText(self.shortcut)

    def focusOutEvent(self, event):
        return super().focusOutEvent(event)

    def keyPressEvent(self, event):
        key = event.key()

        # 忽略重复按键事件
        if event.isAutoRepeat():
            return

        modifiers = event.modifiers()
        if key == Qt.Key_Escape:
            self.clear()
            return

        # 如果按下的是Enter/Return，完成录制
        if key in (Qt.Key_Return, Qt.Key_Enter):
            self.clearFocus()
            return

        # 忽略单独的修饰键
        if key in (Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta):
            return

        # 添加修饰键
        self.shortcut = QKeySequence(modifiers | key).toString()
        self.setText(self.shortcut)


class LabelEdit(LineEdit):
    def __init__(self, text: str = "", parent=None):
        super().__init__(parent=parent)
        self.setText(text)
        self.setReadOnly(True)
        self.setContentsMargins(0, 0, 0, 0)
        self.setMinimumWidth(100)
        self.returnPressed.connect(self.enterPressEvent)

    def mouseDoubleClickEvent(self, event):
        self.setReadOnly(False)
        return super().mouseDoubleClickEvent(event)

    def focusOutEvent(self, event):
        self.setReadOnly(True)
        return super().focusOutEvent(event)

    def enterPressEvent(self):
        self.setReadOnly(True)


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


if __name__ == "__main__":
    import sys
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    window = KeyMacroUI()
    window.show()
    sys.exit(app.exec_())

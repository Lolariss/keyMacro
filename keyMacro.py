import _thread
import time

import keyboard
import mouse

from utils import logger


def mouseMove(offset):
    mouse.move(*offset)


class KeyMacro:
    __EVENT_HANDLER = {
        "default": {
            "key": {
                "up": keyboard.release,
                "down": keyboard.press
            },
            "mouse": {
                "up": mouse.release,
                "down": mouse.press,
                "double": mouse.press,
                "move": mouseMove,
                "wheel": mouse.wheel
            }
        }
    }

    def __init__(self, eventsRecord: list = None):
        self.eventsRecord = [] if eventsRecord is None else eventsRecord
        self.isRecording = False
        self.isPlaying = False
        self.isCallback = True

    def __repr__(self):
        return str(self.eventsRecord)

    def startRecording(self, isKey: bool = True, isMouse: bool = True, isUntil: str = None):
        def waiting():
            keyboard.wait(isUntil)
            self.stopRecording(isKey, isMouse)

        if not self.isRecording:
            self.eventsRecord.clear()
            self.isRecording = True

            if isKey:
                keyboard.hook(self.__recordKeyEvent)
            if isMouse:
                mouse.hook(self.__recordMouseEvent)
            if isUntil is not None:
                _thread.start_new_thread(waiting, ())

    def stopRecording(self, isKey: bool = True, isMouse: bool = True):
        if self.isRecording:
            self.isRecording = False
            if isKey:
                keyboard.unhook(self.__recordKeyEvent)
            if isMouse:
                mouse.unhook(self.__recordMouseEvent)

    def __recordKeyEvent(self, event):
        self.eventsRecord.append({"key": {"key": event.name, "type": event.event_type, "time": event.time}})

    def __recordMouseEvent(self, event):
        if isinstance(event, mouse.ButtonEvent):
            self.eventsRecord.append({"mouse": {"key": event.button, "type": event.event_type, "time": event.time}})
        elif isinstance(event, mouse.MoveEvent):
            self.eventsRecord.append({"mouse": {"offset": [event.x, event.y], "type": "move", "time": event.time}})
        else:
            self.eventsRecord.append({"mouse": {"delta": event.delta, "type": "wheel", "time": event.time}})

    def playRecord(self, keepInterval: bool = True, isLoop: bool = False, delay: int = 0, callback=None, kwargs: dict = None):
        def playing(eventsRecord, keepInterval, isLoop, delay):
            self.isPlaying = True
            try:
                eventHandler = self.__EVENT_HANDLER['default']
                while True:
                    keyTime = next(iter(eventsRecord[0].values()))['time']
                    for event in eventsRecord:
                        if not self.isPlaying:
                            isLoop = False
                            break
                        for eventType, eventRecord in event.items():
                            duration = max(eventRecord['time'] - keyTime, 0)
                            if keepInterval and duration > 0:
                                time.sleep(float(duration))
                            keyTime = eventRecord['time']
                            keyValue = eventRecord['key' if "key" in eventRecord else ('offset' if 'offset' in eventRecord else "delta")]
                            eventHandler[eventType][eventRecord['type']](keyValue)
                    if not isLoop:
                        break
                    if delay > 0:
                        time.sleep(delay / 1000)
                keyboard.restore_state([])
                if callback is not None and self.isCallback:
                    logger.info("calling back...")
                    if isinstance(kwargs, dict):
                        callback(**kwargs)
                    else:
                        callback()
            except Exception as e:
                logger.exception(f"执行宏失败! {e}")
            finally:
                self.isPlaying = False

        if not self.isPlaying and len(self.eventsRecord) > 0:
            self.isCallback = True
            _thread.start_new_thread(playing, (self.eventsRecord, keepInterval, isLoop, delay))

    def terminateRecord(self, isCallback=True):
        self.isPlaying = False
        self.isCallback = isCallback

    def addKeyRecord(self, key, event, msec):
        baseTime = 0 if len(self.eventsRecord) == 0 else next(iter(self.eventsRecord[-1].values()))['time']
        time = msec / 1000
        self.eventsRecord.append({"key": {"key": key, "type": event, "time": baseTime + time}})

    def addMouseRecord(self, key, event, msec):
        baseTime = 0 if len(self.eventsRecord) == 0 else next(iter(self.eventsRecord[-1].values()))['time']
        time = msec / 1000
        if event == 'move':
            self.eventsRecord.append({"mouse": {"offset": key, "type": "move", "time": baseTime + time}})
        elif event == 'wheel':
            self.eventsRecord.append({"mouse": {"delta": key, "type": "wheel", "time": baseTime + time}})
        elif key in {'left', 'right', 'middle'}:
            self.eventsRecord.append({"mouse": {"key": key, "type": event, "time": baseTime + time}})
        else:
            raise Exception('error mouse record!')

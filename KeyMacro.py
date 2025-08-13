import _thread
import time

import keyboard
import mouse


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

    def __repr__(self):
        return str(self.eventsRecord)

    def startRecording(self, isKey: bool = True, isMouse: bool = True, isUntil: str = None):
        def waiting():
            keyboard.wait(isUntil)
            self.stopRecording()

        if not self.isRecording:
            self.eventsRecord.clear()
            self.isRecording = True

            if isKey:
                keyboard.hook(self.__recordKeyEvent)
            if isMouse:
                mouse.hook(self.__recordMouseEvent)
            if isUntil is not None:
                _thread.start_new_thread(waiting, ())

    def stopRecording(self):
        if self.isRecording:
            self.isRecording = False
            keyboard.unhook_all()
            mouse.unhook_all()

    def __recordKeyEvent(self, event):
        self.eventsRecord.append({"key": {"key": event.name, "type": event.event_type, "time": event.time}})

    def __recordMouseEvent(self, event):
        if isinstance(event, mouse.ButtonEvent):
            self.eventsRecord.append({"mouse": {"key": event.button, "type": event.event_type, "time": event.time}})
        elif isinstance(event, mouse.MoveEvent):
            self.eventsRecord.append({"mouse": {"offset": (event.x, event.y), "type": "move", "time": event.time}})
        else:
            self.eventsRecord.append({"mouse": {"delta": event.delta, "type": "wheel", "time": event.time}})

    def playRecord(self, keepInterval: bool = True, isLoop: bool = False, callback=None):
        def playing(eventsRecord, keepInterval, isLoop):
            self.isPlaying = True
            try:
                eventHandler = self.__EVENT_HANDLER['default']
                while True:
                    startTime = 0
                    for event in eventsRecord:
                        if not self.isPlaying:
                            isLoop = False
                            break
                        for eventType, eventRecord in event.items():
                            if keepInterval and startTime:
                                duration = max(eventRecord['time'] - startTime, 0)
                                time.sleep(float(duration))
                            startTime = eventRecord['time']
                            keyValue = eventRecord['key' if "key" in eventRecord else ('offset' if 'offset' in eventRecord else "delta")]
                            eventHandler[eventType][eventRecord['type']](keyValue)
                    if not isLoop:
                        break
                if callback is not None:
                    callback()
            except Exception as e:
                print(f"执行宏失败! {e}")
            finally:
                self.isPlaying = False

        if not self.isPlaying and len(self.eventsRecord) > 0:
            _thread.start_new_thread(playing, (self.eventsRecord, keepInterval, isLoop))

    def terminateRecord(self):
        self.isPlaying = False

    def addKeyRecord(self, key, event, msec):
        baseTime = 0 if len(self.eventsRecord) == 0 else next(iter(self.eventsRecord[-1].values()))['time']
        time = msec / 1000
        self.eventsRecord.append({"key": {"key": key, "type": event, "time": baseTime + time}})

    def addMouseRecord(self, key, event, msec):
        baseTime = 0 if len(self.eventsRecord) == 0 else next(iter(self.eventsRecord[-1].values()))['time']
        time = msec / 1000
        if key in {'left', 'right', 'middle'}:
            self.eventsRecord.append({"mouse": {"key": key, "type": event, "time": baseTime + time}})
        elif event == 'move':
            self.eventsRecord.append({"mouse": {"offset": key, "type": "move", "time": baseTime + time}})
        elif event == 'wheel':
            self.eventsRecord.append({"mouse": {"delta": key, "type": "wheel", "time": baseTime + time}})
        else:
            raise Exception('error mouse record!')

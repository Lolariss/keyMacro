import logging
import ujson

from pathlib import Path


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


def initLogger(name: str = "logs", maxBytes: int = 0):
    logsPath = Path.cwd() / f"{name}.log"
    if logsPath.exists() and 0 < maxBytes < logsPath.stat().st_size:
        logsPath.unlink()

    if name in logging.Logger.manager.loggerDict:
        return logging.getLogger(name)

    formatter = logging.Formatter("%(asctime)s [%(threadName)s] %(name)s (%(filename)s:%(lineno)d) %(levelname)s - %(message)s")
    fileHandler = logging.FileHandler(str(logsPath), delay=True, encoding='utf-8')
    fileHandler.setFormatter(formatter)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(streamHandler)
    logger.addHandler(fileHandler)
    return logger


logger = initLogger("keyMacro", 10 * 1048576)

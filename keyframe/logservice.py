from __future__ import print_function
from __future__ import absolute_import
import time
import logging
from logging import StreamHandler
from logging.handlers import WatchedFileHandler
import uuid
import json
import os, sys

#### -- Global logging ---- #####


LOG_LEVEL = os.getenv("KEYFRAME_LOG", "info")


LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

LEVEL = LEVELS[LOG_LEVEL]
MAX_LOG_LENGTH = os.getenv("KEYFRAME_MAX_LOG_LENGTH", "200")
LOG_FORMAT = f"[%(levelname)1.1s %(asctime)s %(name)s] %(message).{MAX_LOG_LENGTH}s"
if MAX_LOG_LENGTH == "0":
    LOG_FORMAT = "[%(levelname)1.1s %(asctime)s %(name)s] %(message)s"

def createKeyframeHandler():
    handler = None
    # Specify the full path via MYRA_LOGFILE otherwise will default.
    logfile = os.getenv("KEYFRAME_LOGFILE")
    if not logfile:
        handler = StreamHandler()
    else:
        logfile_suffix = os.getenv("KEYFRAME_LOGFILE_SUFFIX")
        if logfile_suffix == "pid":
            logfile = logfile + ".%s" % (os.getpid(),)
        handler = WatchedFileHandler(logfile)
    #handler.setLevel(LEVEL)
    #handler.setFormatter()
    return handler

#handler = None
# def getHandler():
#     global handler
#     if not handler:
#         handler = createHandler()
#     return handler

# def _setupLogger(moduleName=None):
#     logger = logging.getLogger(moduleName)
#     logger.setLevel(LEVEL)

#     handler = getHandler()
#     formatter = logging.Formatter(LOG_FORMAT)
#     handler.setFormatter(formatter)
#     logger.addHandler(handler)
#     return logger

# Setup the logger for all modules under keyframe.
# By setting up keyframe vs () (i.e. root), only myra modules will
# use this - so we won't get info/debug logs from third party modules.
#_logger = _setupLogger("keyframe")
#_logger = _setupLogger()
#_logger.setLevel(LEVEL)
#_logger.debug("logging level DEBUG")
#_logger.info("logging level INFO")
#_logger.warn("logging level WARN")
#_logger.error("logging level ERROR")

def getLogger(moduleName):
    return logging.getLogger(moduleName)

def resetRootHandler():
    print("resetRootHandler called")
    global handler
    root_logger = logging.getLogger()
    for h in root_logger.handlers:
        root_logger.removeHandler(h)
    print("removed existing handlers from root_logger")
    #root_logger.addHandler(logging.NullHandler())

def setupHandlers():
    rootHandler = createKeyframeHandler()
    rootFormatter = logging.Formatter(LOG_FORMAT)
    rootHandler.setFormatter(rootFormatter)
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.WARNING)
    rootLogger.addHandler(rootHandler)

    #keyframeHandler = createKeyframeHandler()
    #keyframeFormatter = logging.Formatter(LOG_FORMAT)
    #keyframeHandler.setFormatter(keyframeFormatter)
    keyframeLogger = logging.getLogger("keyframe")
    keyframeLogger.setLevel(LEVEL)
    #keyframeLogger.addHandler(keyframeHandler)


resetRootHandler()
setupHandlers()

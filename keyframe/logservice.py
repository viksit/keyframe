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

def resetRootHandler():
    print("resetRootHandler called")
    global handler
    root_logger = logging.getLogger()
    for h in root_logger.handlers:
        root_logger.removeHandler(h)
    print("removed existing handlers from root_logger")
    #root_logger.addHandler(logging.NullHandler())

def setupHandlers(
        logFormat=LOG_FORMAT, rootLogLevel=logging.WARNING,
        keyframeLogLevel=logging.INFO):
    # Set up a single handler with the format LOG_FORMAT at the root.
    # Make the root logger level WARNING so can see any warning from other libraries.
    # Make the keyframe logger level INFO so all keyframe modules can 
    rootHandler = createKeyframeHandler()
    rootFormatter = logging.Formatter(LOG_FORMAT)
    rootHandler.setFormatter(rootFormatter)
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.WARNING)
    rootLogger.addHandler(rootHandler)

    keyframeLogger = logging.getLogger("keyframe")
    keyframeLogger.setLevel(LEVEL)



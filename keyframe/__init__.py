import os, sys
import traceback

# -------- logging ------
import logging
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())

_keyframe_log_level = os.getenv("KEYFRAME_LOG_LEVEL")
if _keyframe_log_level:
    try:
        kll = int(_keyframe_log_level)
        logging.getLogger(__name__).setLevel(kll)
        print >> sys.stderr, "setting keyframe loglevel for %s to %s" % (
            __name__, kll)
    except:
        print >> sys.stderr, "exception setting up logging"
        traceback.print_exc()
        pass
# ----------

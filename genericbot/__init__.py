from __future__ import absolute_import
from __future__ import print_function
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

_genericbot_log_level = os.getenv("GENERICBOT_LOG_LEVEL")
if _genericbot_log_level:
    try:
        kll = int(_genericbot_log_level)
        logging.getLogger(__name__).setLevel(kll)
        print("setting genericbot loglevel for %s to %s" % (
            __name__, kll), file=sys.stderr)
    except:
        print("exception setting up logging", file=sys.stderr)
        traceback.print_exc()
        pass
# ----------

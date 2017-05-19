import os
import datetime
import logging

import boto3

import keyframe.config

log = logging.getLogger(__name__)


WRITER_TYPE_FILE = "file"
WRITER_TYPE_DEVNULL = "devnull"

_writer = None
def getWriter():
    global _writer
    if not _writer:
        writerType = os.getenv("KEYFRAME_EVENT_WRITER_TYPE",
                               WRITER_TYPE_FILE)
        if writerType == WRITER_TYPE_FILE:
            _writer = FileWriter()
        elif writerType == WRITER_TYPE_DEVNULL:
            _writer = DevNullWriter()
    return _writer

class Writer(object):
    def write(self, eventJson):
        raise NotImplementedError()

class DevNullWriter(Writer):
    def write(self, eventJson):
        log.debug("devnull writer dropping event")


class FileWriter(Writer):
    def __init__(self, f=None):
        self.f = f
        if not f:
            ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            self.f = os.getenv(
                "KEYFRAME_EVENT_WRITER_FILE",
                "/tmp/keyframe_events.%s.txt" % (ts,))
        log.info("opening file for writer: %s", self.f)
        self.fd = open(self.f, "a")

    def write(self, s):
        self.fd.write("%s\n" % (s,))
        self.fd.flush()

    def _close(self):
        self.fd.close()
        log.info("closing file event writer (%s)", self.f)

    def __del__(self):
        self._close()

class KinesisStreamWriter(Writer):
    def __init__(self, config=None):
        self.config = config
        if not self.config:
            self.config = keyframe.config.getConfig()
        self.kstream = boto3.client(
            'kinesis',
            region_name=self.config.KINESIS_AWS_REGION,
            aws_access_key_id=self.config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self.config.AWS_SECRET_ACCESS_KEY)

    def write(self, s):
        self.kstream.put_record(
            StreamName=self.config.KINESIS_STREAM_NAME

def test():
    w = getWriter()
    w.write("event1")
    w.write("event2")
    w._close()
    w2 = FileWriter(f=w.f)
    w2.write("event3")


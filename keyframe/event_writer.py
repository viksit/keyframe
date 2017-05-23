import os
import datetime
import logging
import json

import boto3

import keyframe.config

log = logging.getLogger(__name__)


WRITER_TYPE_FILE = "file"
WRITER_TYPE_KINESIS = "kinesis"
WRITER_TYPE_DEVNULL = "devnull"

_writer = None
def getWriter():
    global _writer
    if not _writer:
        writerType = os.getenv("KEYFRAME_EVENT_WRITER_TYPE",
                               WRITER_TYPE_KINESIS)
        if writerType == WRITER_TYPE_FILE:
            _writer = FileWriter()
        elif writerType == WRITER_TYPE_DEVNULL:
            _writer = DevNullWriter()
        elif writerType == WRITER_TYPE_KINESIS:
            _writer = KinesisStreamWriter()
        else:
            raise Exception("Unknown event writer type (%s)", writerType)
    return _writer

class Writer(object):
    def write(self, eventJson):
        raise NotImplementedError()

class DevNullWriter(Writer):
    def write(self, data, partitionKey=None):
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

    def write(self, data, partitionKey=None):
        self.fd.write("%s\n" % (data,))
        self.fd.flush()

    def _close(self):
        self.fd.close()
        log.info("closing file event writer (%s)", self.f)

    def __del__(self):
        self._close()

class KinesisStreamWriter(Writer):
    def __init__(self, config=None, kinesisStreamName=None):
        self.config = config
        if not self.config:
            self.config = keyframe.config.getConfig()
        self.kstream = boto3.client(
            'kinesis',
            region_name=self.config.KINESIS_AWS_REGION,
            aws_access_key_id=self.config.KINESIS_USER_ACCESS_KEY_ID,
            aws_secret_access_key=self.config.KINESIS_USER_SECRET_ACCESS_KEY)
        self.kinesisStreamName = kinesisStreamName
        if not self.kinesisStreamName:
            self.kinesisStreamName = self.config.KINESIS_STREAM_NAME
        log.info("created KinesisStreamWriter with kstreamname: %s", self.kinesisStreamName)

    def write(self, data, partitionKey):
        self.kstream.put_record(
            StreamName=self.kinesisStreamName,
            Data=data,
            PartitionKey=partitionKey)
        log.info("put record into kstream")

def testFileWriter():
    w = FileWriter()
    w.write("event1")
    w.write("event2")
    w._close()
    w2 = FileWriter(f=w.f)
    w2.write("event3")

def testKinesisWriter():
    w = KinesisStreamWriter()
    w.write(json.dumps({"event_id":"1234", "user_id":"u1"}), "u1")
    w.write(json.dumps({"event_id":"1235", "user_id":"u2"}), "u2")
    w.write(json.dumps({"event_id":"1236", "user_id":"u3"}), "u3")
    w.write(json.dumps({"event_id":"1237", "user_id":"u1"}), "u1")


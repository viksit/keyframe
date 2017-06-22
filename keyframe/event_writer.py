import os
import datetime
import logging
import json

import boto3

import keyframe.config

log = logging.getLogger(__name__)
#log.setLevel(10)

WRITER_TYPE_FILE = "file"
WRITER_TYPE_KINESIS = "kinesis"
WRITER_TYPE_DEVNULL = "devnull"

_writerCache = {}
def getWriter(streamName=None, streamSuffix=None, config=None, writerType=None):
    global _writerCache
    k = (streamName, streamSuffix, config, writerType)
    _writer = _writerCache.get(k)
    if _writer:
        return _writer
    _writer = createWriter(
        streamName=streamName, streamSuffix=streamSuffix,
        config=config, writerType=writerType)
    _writerCache[k] = _writer
    return _writer

def createWriter(streamName=None, streamSuffix=None, config=None, writerType=None):
    writer = None
    if not writerType:
        writerType = os.getenv("KEYFRAME_EVENT_WRITER_TYPE",
                               WRITER_TYPE_KINESIS)

    if writerType == WRITER_TYPE_DEVNULL:
        writer = DevNullWriter()
        return writer

    if not config:
        config = keyframe.config.getConfig()

    assert not (streamName and streamSuffix), \
        "Cannot specify both streamName and streamSuffix"
    assert (streamName or streamSuffix), \
        "Must specify one of streamName or streamSuffix"

    kStreamName = streamName
    if not kStreamName:
        kStreamName = "%s-%s" % (
            config.KINESIS_STREAM_PREFIX,
            streamSuffix)

    if writerType == WRITER_TYPE_FILE:
        f = "/tmp/%s" % (kStreamName,)
        writer = FileWriter(f=f)
    elif writerType == WRITER_TYPE_KINESIS:
        writer = KinesisStreamWriter(
            config=config, kinesisStreamName=kStreamName)
    else:
        raise Exception("Unknown event writer type (%s)", writerType)
    return writer

class Writer(object):
    def write(self, eventJson):
        raise NotImplementedError()

class DevNullWriter(Writer):
    def write(self, data, partitionKey=None):
        log.debug("devnull writer dropping event")


class FileWriter(Writer):
    def __init__(self, f=None):
        self.f = f
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
    def __init__(self, config, kinesisStreamName):
        self.config = config
        self.kstream = boto3.client(
            'kinesis',
            region_name=self.config.KINESIS_AWS_REGION,
            aws_access_key_id=self.config.KINESIS_USER_ACCESS_KEY_ID,
            aws_secret_access_key=self.config.KINESIS_USER_SECRET_ACCESS_KEY)
        self.kinesisStreamName = kinesisStreamName
        log.info("created KinesisStreamWriter with kstreamname: %s", self.kinesisStreamName)

    def write(self, data, partitionKey):
        log.debug("KinesisStreamWriter.write(%s)", locals())
        self.kstream.put_record(
            StreamName=self.kinesisStreamName,
            Data=data,
            PartitionKey=partitionKey)
        log.info("wrote to streamname: %s", self.kinesisStreamName)

def testFileWriter():
    w = FileWriter()
    w.write("event1")
    w.write("event2")
    w._close()
    w2 = FileWriter(f=w.f)
    w2.write("event3")

def testKinesisWriter(config=None, kinesisStreamName=None, numEvents=1):
    w = KinesisStreamWriter(config, kinesisStreamName)
    for i in range(numEvents):
        w.write(json.dumps({"event_id":"1234", "user_id":"u1"}), "u1")



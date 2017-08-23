"""
Write to s3.
Do not add any dependencies in here except those required to write to s3.
This module is used in lambda functions, and it is better without many dependencies.
"""

import json
import logging
import os.path
import uuid
import datetime
import StringIO
import time

import boto
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from boto.s3.bucketlistresultset import BucketListResultSet

log = logging.getLogger(__name__)

class S3Writer(object):
    def __init__(self, s3Bucket, config=None):
        log.info("S3Writer.__init__(%s) called", locals())
        self.s3Bucket = s3Bucket
        self.config = config

    def _dt(self):
        return datetime.datetime.utcnow().strftime("%Y/%m/%d/%H")
        #return datetime.datetime.utcnow().strftime("%Y/%m/%d/%H/%M/%S")

    def _get_conn(self):
        # If keys are not explicitly passed in via config, they need
        # to be in the environment.
        # boto.connect_s3 will look for AWS_ACCESS_KEY_ID and AWS_ACCESS_KEY_ID
        # as environment variables.
        aws_access_key_id = None
        if self.config and hasattr(self.config, "AWS_ACCESS_KEY_ID"):
            aws_access_key_id = self.config.AWS_ACCESS_KEY_ID
        aws_secret_access_key = None
        if self.config and hasattr(self.config, "AWS_SECRET_ACCESS_KEY"):
            aws_secret_access_key = self.config.AWS_SECRET_ACCESS_KEY
        conn = boto.connect_s3(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key)
        return conn

    def _get_key_dt(self, s3Prefix):
        conn = self._get_conn()
        b = conn.get_bucket(self.s3Bucket)
        k = Key(b)
        ks = "%s/%s/%s-%s" % (
            s3Prefix.strip("/"),
            self._dt(),
            int(time.time()),
            str(uuid.uuid4()))
        log.info("creating key: %s, (bucket: %s)", ks, self.s3Bucket)
        k.key = ks
        return k

    def writeTs(self, s3Prefix, s):
        """Write s to s3 with a key or path with a UTC datetime.
        s: string
        """
        k = self._get_key_dt(s3Prefix)
        k.set_contents_from_string(s)
        k.close()

    def writeJsonData(self, s3Prefix, j):
        """Write j to s3.
        j: a sequence of json-compatible objects.
        """
        s = StringIO.StringIO()
        for e in j:
            s.write("%s\n" % (json.dumps(e),))
        self.writeTs(s3Prefix, s.getvalue())

    def writeData(self, s3Prefix, data):
        """Write j to s3.
        j: a sequence of json-compatible objects.
        """
        s = StringIO.StringIO()
        for e in data:
            s.write("%s\n" % (e,))
        self.writeTs(s3Prefix, s.getvalue())

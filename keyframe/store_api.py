import os, sys
import json
import logging

import boto3
from boto.s3.connection import S3Connection
from boto.s3.key import Key

import boto.dynamodb
from boto.dynamodb.exceptions import DynamoDBKeyNotFoundError


log = logging.getLogger(__name__)
# To debug, just set the level for this module.
#log.setLevel(10)

TYPE_S3 = "type-s3"
TYPE_DYNAMODB = "type-dynamodb"
TYPE_LOCALFILE = "type-localfile"
TYPE_INMEMORY = "type-inmemory"

def get_kv_store(kvstype, config):
    if not kvstype:
        kvstype = TYPE_LOCALFILE
    if kvstype == TYPE_S3:
        conn = S3Connection(
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY)
        b = conn.get_bucket(config.KV_STORE_S3_BUCKET)
        return S3KVStore(b)
    elif kvstype == TYPE_DYNAMODB:
        dbconn = boto.dynamodb.connect_to_region(
            config.DYNAMODB_AWS_REGION,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY)
        return DynamoKVStore(dbconn, config.KV_STORE_DYNAMODB_TABLE)
    elif kvstype == TYPE_LOCALFILE:
        return LocalFileKVStore()
    elif kvstype == TYPE_INMEMORY:
        return InMemoryKVStore()
    else:
        raise Exception("unknown kvstore: %s", kvstype)

class KVStoreError(Exception):
    pass

class KVStore(object):
    def put(self, key, value, expiry_time=None):
        """Input:
        key: (string)
        value: (string)
        """
        raise NotImplementedError()

    def get(self, key):
        """Input:
        key: (string)
        Returns: (string)
        """
        raise NotImplementedError()

    def delete(self, key):
        raise NotImplementedError()

    def get_json(self, key, default=None):
        """Input:
        key: (string)
        Returns: A python object corresponding to the value loaded as json.
        If value is not a json string, will throw back
        the exception thrown by json.loads.
        """
        s = self.get(key)
        if not s:
            log.info("key:%s not found, returning default", key)
            return default
        log.info("found key:%s, returning json", key)
        return json.loads(s)

    def put_json(self, key, value, expiry_time=None):
        """Input
        key: (string)
        value: a python object that can be dumped as json.
        """
        self.put(key, json.dumps(value), expiry_time)


# Useful in unit tests and potentially local testing.
# Biggest advantage over LocalFileKVStore is for unit tests
# just create a new store to start with a clean store.
class InMemoryKVStore(KVStore):
    def __init__(self):
        log.info("InMemoryKVStore.__init__")
        self.d = {}

    def put(self, key, value, expiry_time=None):
        """Input:
        key: (string)
        value: (string)
        """
        log.info("InMemoryKVStore.put(%s)", locals())
        self.d[key] = value

    def get(self, key):
        """Input:
        key: (string)
        Returns: (string)
        """
        log.info("InMemoryKVStore.get(%s)", locals())
        return self.d.get(key)

    def delete(self, key):
        if key in self.d:
            self.d.pop(key)

class LocalFileKVStore(KVStore):
    def __init__(self, local_dir="/mnt/tmp"):
        self.local_dir = local_dir

    def put(self, key, value, expiry_time=None):
        with open(self.local_dir + "/" + key, "w") as f:
            f.write(value)
        if expiry_time:
            with open(self.local_dir + "/" + key + ".meta", "w") as f:
                f.write("expiry_time=%s\n" % (expiry_time,))


    def get(self, key):
        p = self.local_dir + "/" + key
        if not os.path.exists(p):
            log.info("path:%s does not exist", p)
            return None
        with open(self.local_dir + "/" + key, "r") as f:
            return f.read()

    def delete(self, key):
        p = self.local_dir + "/" + key
        if os.path.exists(p):
            os.remove(p)

class DynamoKVStore(KVStore):
    def __init__(self, dbconn, db_table):
        self.dbconn = dbconn
        self.kvstore = dbconn.get_table(db_table)

    def put(self, key, value, expiry_time=None):
        log.debug("DynamoKVStore.put(%s)", locals())
        attrs = {"kv_key":key, "kv_value":value}
        if expiry_time:
            attrs["expiry_time"] = expiry_time
        i = self.kvstore.new_item(
            hash_key=key, attrs=attrs)
        i.put()

    def get(self, key):
        log.debug("DynamoKVStore.get(%s)", locals())
        try:
            i = self.kvstore.get_item(
                hash_key=key)
            return i["kv_value"]  # Must be there, or there is something wrong
        except DynamoDBKeyNotFoundError as de:
            return None

    def delete(self, key):
        log.info("DynamoKVStore.delete(%s)", locals())
        try:
            i = self.kvstore.get_item(
                hash_key=key)
            i.delete()
        except DynamoDBKeyNotFoundError as de:
            pass

    def __repr__(self):
        return "%s()" % (self.__class__,)

class S3KVStore(KVStore):
    def __init__(self, s3Bucket):
        self.s3Bucket = s3Bucket

    def put(self, key, value, expiry_time=None):
        k = Key(self.s3Bucket)
        k.key = "nishant/r29/dbkvstore/%s" % (key,)
        k.set_contents_from_string(value)

    def get(self, key):
        k = Key(self.s3Bucket)
        k.key = "nishant/r29/dbkvstore/%s" % (key,)
        if k.exists():
            return k.get_contents_as_string(encoding="utf-8")
        return None

    def delete(self, key):
        k = Key(self.s3Bucket)
        k.key = "nishant/r29/dbkvstore/%s" % (key,)
        if k.exists():
            k.delete()

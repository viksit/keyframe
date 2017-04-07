from __future__ import print_function

import traceback
import os
import logging
import time
import random
import uuid
import tempfile
import requests

from store_api import KVStore, KVStoreError

def getLogLevel(envVar, defaultLogLevel=logging.INFO):
    l = os.getenv(envVar, defaultLogLevel)
    try:
        ll = int(l)
        return ll
    except ValueError as ve:
        traceback.print_exc()
        return defaultLogLevel

class PersistentDict(object):
    def __init__(self, kvStore, kvStoreKey):
        self.kvStoreKey = kvStoreKey
        self.kvStore = kvStore

    def _getDict(self):
        return self.kvStore.get_json(self.kvStoreKey, {})

    def get(self, key):
        d = self._getDict()
        logging.info("d: %s", d)
        return d.get(key)

    def add(self, key, value):
        if not isinstance(key, basestring):
            raise KVStoreError("key must be of type basestring")
        d = self._getDict()
        d[key] = value
        self.kvStore.put_json(self.kvStoreKey, d)

    def remove(self, key):
        d = self._getDict()
        if d:
            if key in d:
                d.pop(key)
                self.kvStore.put_json(self.kvStoreKey, d)

    def clear(self):
        self.kvStore.delete(self.kvStoreKey)

class CachedPersistentDict(PersistentDict):
    def __init__(self, kvStore, kvStoreKey):
        super(self.__class__, self).__init__(kvStore, kvStoreKey)
        self.cacheDict = self._getDict()

    def get(self, key):
        return self.cacheDict.get(key)

    def add(self, key, value):
        super(self.__class__, self).add(key, value)
        self.cacheDict[key] = value

    def remove(self, key):
        super(self.__class__, self).remove(key)
        if key in self.cacheDict:
            self.cacheDict.pop(key)

    def clear(self):
        super(self.__class__, self).clear()
        self.cacheDict = {}

    def __repr__(self):
        return "%s" % (self.cacheDict,)

def getUUID():
    return str(uuid.uuid4()).replace("-", "")

def timestampUid():
    return "%i_%s" % (round(time.time()*1000), random.randint(0,1000))

def urlToFD(url, sizeLimitBytes=None, chunkSize=100000):
    f = tempfile.TemporaryFile()
    r = requests.get(url, stream=True)
    if not r.status_code in (200, 201):
        raise Exception("could not get url. status_code: %s" % (r.status_code,))
    for chunk in r.iter_content(chunk_size=chunkSize):
        f.write(chunk)
    f.seek(0)
    return (f, r.headers.get("Content-Type"))

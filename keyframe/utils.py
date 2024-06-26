from __future__ import print_function

from __future__ import absolute_import
import traceback
import os
import logging
import time
import random
import uuid
import tempfile
import requests

from .store_api import KVStore, KVStoreError
import six

def getFromFileOrDefault(filePath, defaultValue):
    v = defaultValue
    if os.path.isfile(filePath):
        v = open(filePath).readline()
        if v:
            v = v.strip()
    #log.info("getFromFileOrDefault returns %s", v)
    return v

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
        if not isinstance(key, six.string_types):
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

# Pretty-print (kind of) a dict.
def pretty(d, indent=0):
   for key, value in d.items():
      print('\t' * indent + str(key))
      if isinstance(value, dict):
         pretty(value, indent+1)
      else:
         print('\t' * (indent+1) + str(value))

def urlToFD2(url, sizeLimitBytes=None, chunkSize=100000):
    f = tempfile.TemporaryFile()
    r = requests.get(url, stream=True)
    if not r.status_code in (200, 201):
        raise Exception("could not get url. status_code: %s" % (r.status_code,))
    for chunk in r.iter_content(chunk_size=chunkSize):
        f.write(chunk)
        log.debug("got chunk (%s)", f.tell())
    f.seek(0)
    return (f, r.headers.get("Content-Type"))

def urlToFD(url, sizeLimitBytes=None, chunkSize=100000):
    f = tempfile.TemporaryFile()
    r = requests.get(url)
    if not r.status_code in (200, 201):
        raise Exception("could not get url. status_code: %s" % (r.status_code,))
    f.write(r.content)
    f.seek(0)
    return (f, r.headers.get("Content-Type"))

def getContentType(f):
    x = os.path.splitext(f)
    if x[1] in ("png", "jpeg", "gif", "bmp", "webp"):
        return "image/%s" % (x[1],)
    return "application/octet-stream"


def fOnV(d, ft, fn):
    """
    Apply fn to all values in d if ft(value) is true.
    Changes d in place. Leaves all values where not ft(value) as they are.
    For example, capitalize all string values in d. 
      ft = lambda x: isinstance(x, str)
      fn = lambda x: x.capitalize()
    """
    assert isinstance(d, dict)
    for (k,v) in six.iteritems(d):
        if ft(v):
            d[k] = fn(v)
        elif isinstance(v, dict):
            fOnV(v, ft, fn)


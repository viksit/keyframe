from __future__ import print_function
import logging

import messages
import slot_fill
import copy
import misc
import uuid
from collections import defaultdict
import sys
from m5 import BaseBot

from six import iteritems, add_metaclass


log = logging.getLogger(__name__)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
logformat = "[%(levelname)1.1s %(asctime)s %(name)s] %(message)s"
formatter = logging.Formatter(logformat)
ch.setFormatter(formatter)
log.addHandler(ch)
log.setLevel(logging.DEBUG)
log.propagate = False


def getUUID():
    return str(uuid.uuid4()).replace("-", "")

class ActionObjectError(Exception):
    pass

class ActionObject(object):

    """
    A user declares an action object.
    Each action object contains a bunch of slots.
    Each slot maps to an entity that needs to be given to the process function.
    Each slot is available as a subclass, which we must add to the AO when it is initialized.
    Each AO can be serialized and deserialized from botstate.
    Botstate is stored via the KV store api.
    """

    def __init__(self, **kwargs):
        self.__clsid__ = getUUID()
        self.apiResult = kwargs.get("apiResult")
        self.canonicalMsg = kwargs.get("canonicalMsg")
        self.state = "new"
        self.channelClient = kwargs.get("channelClient")
        self.kvStore = kwargs.get("kvStore")
        self.slotObjects = kwargs.get("slotObjects")
        self.botState = kwargs.get("botState")
        self.init()

    def init(self):
        pass

    def slotFill(self):
        """
        Function to do slot fill per action object.
        """
        log.info("-- slotFill --")
        log.info("slotobjects: %s", self.slotObjects)
        print(self.canonicalMsg, self.apiResult, self.botState, self.channelClient)
        pass

    def process(self):
        raise NotImplementedError()

    def processWrapper(self):
        # Fill slots
        log.info("processWrapper: botState: %s", self.botState)

        # Currently filling
        if self.requestState == BaseBot.REQUEST_STATE_PROCESS_SLOT:
            allFilled = self.slotFill()
            if allFilled is False:
                return
        # New
        elif self.requestState == BaseBot.REQUEST_STATE_NEW:
            allFilled = self.slotFill()
            if allFilled is False:
                return

        # Call process function with slot data in there.
        return self.process()

    @classmethod
    def _createActionObjectKey(cls, canonicalMsg, id):
        k = "%s.%s.%s.%s" % (
            cls.__name__, canonicalMsg.userId,
            canonicalMsg.channel, id)
        return k

    def toJSONObject(self):
        raise NotImplementedError()

    def createAndSendTextResponse(self, canonicalMsg, text, responseType=None):
        cr = messages.createTextResponse(canonicalMsg, text, responseType)
        self.channelClient.sendResponse(cr)

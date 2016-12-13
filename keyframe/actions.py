from __future__ import print_function
import logging

import messages
import slot_fill
import copy
import misc
import uuid
from collections import defaultdict
import sys
from base import BaseBot

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
        self.init()

    def init(self):
        pass

    def resetSlots(self):
        for slotObject in self.slotObjects:
            slotObject.reset()

    def slotFill(self, botState):
        """
        Function to do slot fill per action object.
        Returns:
          True if all slots are filled.
          False if all slots haven't been filled yet or something went wrong.

        """
        for slotObject in self.slotObjects:
            if not slotObject.filled:
                filled = slotObject.fill(
                    self.canonicalMsg, self.apiResult, self.channelClient)
                if filled is False:
                    botState.putWaiting(self.toJSONObject())
                    return False
        # End slot filling
        # Now, all slots for this should be filled.
        allFilled = True
        # Is this necessary?
        for slotObject in self.slotObjects:
            if not slotObject.filled:
                allFilled = False
                break

        # Save state before returning
        # This can be better done as a decorator
        return allFilled


    def process(self):
        """
        The user fills this up.
        """
        raise NotImplementedError()

    def processWrapper(self, botState):
        # Fill slots
        log.info("processWrapper: botState: botstate: %s, reqstate: %s", botState, self.requestState)
        allFilled = self.slotFill(botState)
        if allFilled is False:
            return BaseBot.REQUEST_STATE_PROCESSED

        # Call process function only when slot data is filled up
        requestState = self.process()
        # should we save bot state here?
        # reset slots now that we're filled
        self.resetSlots()
        return requestState

    @classmethod
    def _createActionObjectKey(cls, canonicalMsg, id):
        k = "%s.%s.%s.%s" % (
            cls.__name__, canonicalMsg.userId,
            canonicalMsg.channel, id)
        return k

    def toJSONObject(self):
        # Each action object should have the following things stored
        # Slotobjects
        serializedSlotObjects = [i.toJSONObject() for i in self.slotObjects]

        return {
            "actionObjectClassName": self.__class__.__name__,
            "origIntentStr": self.originalIntentStr,
            "slotObjects": serializedSlotObjects
        }

    @classmethod
    def fromJSONObject(self, jsonObject):
        pass

    def createAndSendTextResponse(self, canonicalMsg, text, responseType=None):
        cr = messages.createTextResponse(canonicalMsg, text, responseType)
        self.channelClient.sendResponse(cr)

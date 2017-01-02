from __future__ import print_function
import logging

import messages
import slot_fill
import copy
import misc
import uuid
from collections import defaultdict
import sys
import constants
import slot_fill

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
        self.filledSlots = {}
        self.init()

    def init(self):
        pass

    def getSlots(self):
        cls = self.__class__
        allClasses = [cls.__getattribute__(cls, i) for i in cls.__dict__.keys() if i[:1] != '_']
        slotClasses = [i for i in allClasses if type(i) is type and issubclass(i, slot_fill.Slot)]
        return slotClasses

    @classmethod
    def createActionObject(
            cls, intentStr, canonicalMsg, botState,
            userProfile, requestState, api, channelClient, actionObjectParams={}):

        """
        Create a new action object from the given data
        canonicalMsg, apiResult, intentStr
        slots, messages, channelClient

        """
        runAPICall = False
        #actionObject = cls(actionObjectParams)
        actionObject = cls()

        # Get the intent string and create an object from it.
        #slotClasses = slot_fill.getSlots(cls)
        slotClasses = actionObject.getSlots()
        slotObjects = []
        for slotClass in slotClasses:
            sc = slotClass()
            sc.entity = getattr(sc, "entity")
            sc.required = getattr(sc, "required")
            sc.parseOriginal = getattr(sc, "parseOriginal")
            sc.parseResponse = getattr(sc, "parseResponse")
            slotObjects.append(sc)
            if sc.entity.needsAPICall:
                runAPICall = True

        actionObject.slotObjects = slotObjects

        # If a flag is set that tells us to make a myra API call
        # Then we invoke it and fill this.
        # This is used for slot fill.
        # Else, this is None.
        if runAPICall:
            apiResult = api.get(canonicalMsg.text)
            actionObject.apiResult = apiResult

        actionObject.canonicalMsg = canonicalMsg
        actionObject.channelClient = channelClient
        actionObject.requestState = requestState
        actionObject.originalIntentStr = intentStr
        actionObject.userProfile = userProfile
        actionObject.botState = botState
        log.debug("createActionObject: %s", actionObject)
        return actionObject

    @classmethod
    def getIntentStrFromJSON(cls, actionObjectJSON):
        return actionObjectJSON.get("origIntentStr")

    def populateFromJson(self, actionObjectJSON):
        """
        Create an action object from a given JSON object
        """
        slotObjectData = actionObjectJSON.get("slotObjects")
        assert len(slotObjectData) == len(self.slotObjects)
        for slotObject, slotData in zip(self.slotObjects, slotObjectData):
            # Get these from the saved state
            slotObject.filled = slotData.get("filled")
            slotObject.value = slotData.get("value")
            slotObject.validated = slotData.get("validated")
            slotObject.state = slotData.get("state")

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
        log.debug("slotFill(%s)", locals())
        for slotObject in self.slotObjects:
            log.debug("slotObject: %s", slotObject)
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
        log.debug("allFilled: %s", allFilled)
        if allFilled is False:
            return constants.BOT_REQUEST_STATE_PROCESSED

        # Call process function only when slot data is filled up
        self.filledSlots = {}
        for s in self.slotObjects:
            self.filledSlots[s.name] = s.value

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

    def respond(self, text, canonicalMsg=None, responseType=None):
        if not canonicalMsg:
            canonicalMsg = self.canonicalMsg
        if not responseType:
            responseType = messages.ResponseElement.RESPONSE_TYPE_RESPONSE

        cr = messages.createTextResponse(
            self.canonicalMsg,
            text,
            responseType)

        self.channelClient.sendResponse(cr)
        return constants.BOT_REQUEST_STATE_PROCESSED

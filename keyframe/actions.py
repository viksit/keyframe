from __future__ import print_function
import logging

import messages
import slot_fill
import copy
import misc
from collections import defaultdict
import sys
import constants
import slot_fill
import utils

from six import iteritems, add_metaclass


log = logging.getLogger(__name__)

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
    #SLOTS_TYPE_SEQUENTIAL = "slots-type-sequential"
    SLOTS_TYPE_CONDITIONAL = "slots-type-conditional"

    #RESPONSE_TYPE_TEXT = "response-type-text"
    #RESPONSE_TYPE_WEBHOOK = "response-type-webhook"
    #RESPONSE_TYPE_ZENDESK = "response-type-zendesk"

    def __init__(self, **kwargs):
        # TODO - get rid of this does not seem to be used
        self.__clsid__ = utils.getUUID()
        self.apiResult = kwargs.get("apiResult")
        self.canonicalMsg = kwargs.get("canonicalMsg")
        self.state = "new"
        self.channelClient = kwargs.get("channelClient")
        self.kvStore = kwargs.get("kvStore")
        self.slotObjects = kwargs.get("slotObjects")
        self.filledSlots = {}
        self.newTopic = kwargs.get("newTopic")
        self.botState = None
        self.init()

    def init(self):
        pass

    def getPreemptWaitingActionThreshold(self):
        return None

    def getClearWaitingAction(self):
        return False

    def getSlots(self):
        cls = self.__class__
        allClasses = [cls.__getattribute__(cls, i) for i in cls.__dict__.keys() if i[:1] != '_']
        slotClasses = [i for i in allClasses if type(i) is type and issubclass(i, slot_fill.Slot)]
        return slotClasses

    def getTopicType(self):
        if self.originalTopicId.startswith("question_"):
            return "resolution"
        elif self.originalTopicId.startswith("topic"):
            return "diagnostic"
        else:
            raise Exception("cannot get topicType (topicId: %s)" % (self.originalTopicId,))

    @classmethod
    def createActionObject(
            cls, topicId, canonicalMsg, botState,
            userProfile, requestState, api, channelClient, actionObjectParams={},
            apiResult=None, newTopic=None):
        log.debug("ActionObject.createActionObject(%s)", locals())
        """
        Create a new action object from the given data
        canonicalMsg, apiResult, intentStr
        slots, messages, channelClient, actionObjectParams, apiResult, newTopic

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
        actionObject.originalTopicId = topicId
        actionObject.userProfile = userProfile
        actionObject.botState = botState
        actionObject.apiResult = apiResult
        actionObject.newTopic = newTopic
        actionObject.instanceId = None
        if newTopic:
            actionObject.instanceId = cls.createActionObjectId()
        actionObject.originalUtterance = None
        if actionObject.newTopic:
            log.debug("set originalUtterance to input (%s)",
                      canonicalMsg.text)
            actionObject.originalUtterance = canonicalMsg.text

        log.debug("createActionObject: %s", actionObject)
        return actionObject

    @classmethod
    def createActionObjectId(cls):
        x = utils.getUUID()
        return "k-ao-%s" % (x[5:],)

    @classmethod
    def getTopicIdFromJSON(cls, actionObjectJSON):
        #return actionObjectJSON.get("origIntentStr")
        return actionObjectJSON.get("topic_id")

    @classmethod
    def getActionObjectClassFromJSON(cls, actionObjectJSON):
        # TODO(now)
        raise NotImplementedError()

    def fromJSONObject(self, actionObjectJSON):
        """
        Create an action object from a given JSON object
        """
        self.originalUtterance = actionObjectJSON.get("originalUtterance")
        self.instanceId = actionObjectJSON.get("instanceId")
        self.nextSlotToFillName = actionObjectJSON.get("nextSlotToFillName")
        log.debug("got originalUtterance from json: %s", self.originalUtterance)
        slotObjectData = actionObjectJSON.get("slotObjects")
        assert len(slotObjectData) == len(self.slotObjects), \
            "action object spec has %s slots, but object saved in state has %s slots" % (len(self.slotObjects), len(slotObjectData))
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
        # NOTE: This is overridden by generic_action slotfill, so effectively
        # it will not be used.
        log.debug("slotFill(%s)", locals())
        for slotObject in self.slotObjects:
            log.debug("slotObject: %s", slotObject)
            if not slotObject.filled:
                filled = slotObject.fill(
                    self.canonicalMsg, self.apiResult, self.channelClient,
                    botState)
                if filled is False:
                    botState.putWaiting(self.toJSONObject())
                    return constants.BOT_REQUEST_STATE_PROCESSED

        # End slot filling
        return constants.BOT_REQUEST_STATE_PROCESSED


    def process(self, botState):
        """
        The user fills this up.
        """
        raise NotImplementedError()

    def processWrapper(self, botState):
        # Old processWrapper called transitionmsg and did response.
        # but now ActionObject is just a shell for slots.
        return self.slotFill(botState)

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
            #"origIntentStr": self.originalIntentStr,
            "origTopicId": self.originalTopicId,
            "slotObjects": serializedSlotObjects,
            "originalUtterance": self.originalUtterance,
            "instanceId": self.instanceId
        }

    # def createAndSendTextResponse(self, canonicalMsg, text, responseType=None):
    #     log.debug("ActionObject.createAndSendTextResponse(%s)", locals())
    #     cr = messages.createTextResponse(
    #         canonicalMsg, text, responseType,
    #         responseMeta=messages.ResponseMeta(
    #             apiResult=self.apiResult,
    #             newTopic=self.newTopic,
    #             intentStr=self.originalIntentStr,
    #             actionObjectInstanceId=self.instanceId))
    #     self.channelClient.sendResponse(cr)


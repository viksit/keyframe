from __future__ import print_function
import logging

import messages
import slot_fill
import copy
import misc
from collections import defaultdict
import sys
import utils
from bot_state import BotState

from six import iteritems, add_metaclass


# TODO: move logging out into a nicer function/module

log = logging.getLogger(__name__)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
logformat = "[%(levelname)1.1s %(asctime)s %(name)s] %(message)s"
formatter = logging.Formatter(logformat)
ch.setFormatter(formatter)
log.addHandler(ch)
log.setLevel(logging.DEBUG)
log.propagate = False

class BaseBot(object):

    botStateClass = BotState

    # Constants
    REQUEST_STATE_NEW = "req_new"
    REQUEST_STATE_PROCESSED = "req_processed"

    # User profile keys
    UP_NAME = "up_name"

    def __init__(self, *args, **kwargs):

        self.api = kwargs.get("api")
        # TODO(viksit): is this needed?
        self.channelClient = kwargs.get("channelClient")
        self.kvStore = kwargs.get("kvStore")
        self.config = kwargs.get("config")
        self.debug = kwargs.get("debug")

        # self.slotFill = slot_fill.SlotFill()

        self.intentActions = {}
        self.intentThresholds = {}
        self.keywordIntents = {}
        self.regexIntents = {}
        self.intentSlots = defaultdict(lambda: [])
        self.debug = True

        self.init()

    def init(self):
        # Override to initialize stuff in derived bots
        pass

    # Bot state related functions

    def getUserProfile(self, userId, channel):

        userProfileKey = "%s.userprofile.%s.%s" % (
            self.__class__.__name__, userId, channel)

        userProfile = utils.CachedPersistentDict(
            kvStore=self.kvStore,
            kvStoreKey=userProfileKey)

        userName = userProfile.get(self.UP_NAME)

        if not userName:
            channelUserProfile = self.channelClient.getChannelUserProfile(userId)
            if channelUserProfile:
                userProfile.add(self.UP_NAME, channelUserProfile.firstName)
        log.info("BaseBot.getUserProfile returning: %s", userProfile)
        return userProfile

    def _botStateKey(self, userId, channel):
        k = "botstate.%s.%s.%s" % (
            self.__class__.__name__, userId, channel)
        return k

    def getBotState(self, userId, channel):
        k = self._botStateKey(userId, channel)
        jsonObject = self.kvStore.get_json(k)
        if not jsonObject:
            return self.botStateClass()
        return self.botStateClass.fromJSONObject(jsonObject)

    def putBotState(self, userId, channel, botState):
        k = self._botStateKey(userId, channel)
        self.kvStore.put_json(k, botState.toJSONObject())

    # Channel and I/O related functions
    def setChannelClient(self, cc):
        self.channelClient = cc

    def createAndSendTextResponse(self, canonicalMsg, text, responseType=None):
        log.info("createAndSendTextResponse(%s)", locals())
        cr = messages.createTextResponse(canonicalMsg, text, responseType)
        log.info("cr: %s", cr)
        self.channelClient.sendResponse(cr)

    def errorResponse(self, canonicalMsg):
        self.createAndSendTextResponse(
            canonicalMsg, "Internal Error",
            messages.ResponseElement.RESPONSE_TYPE_RESPONSE)


    # Decorators
    # keyword intent, regex intent
    def intent(self, intentStr, **args):
        def myfun(cls):

            # Find the slots associated with action
            slotClasses = slot_fill.getSlots(cls)
            for slotClass in slotClasses:
                sc = slotClass()
                sc.entityType = getattr(sc, "entityType")
                sc.required = getattr(sc, "required")
                sc.parseOriginal = getattr(sc, "parseOriginal")
                sc.parseResponse = getattr(sc, "parseResponse")
                self.intentSlots[intentStr].append(sc)

            # Instantiate action object
            wrapped = cls(**args)
            self.intentActions[intentStr] = wrapped

            class Wrapper(object):
                def __init__(self, *args):
                    self.wrapped = cls(*args)
                    self.intentActions[intentStr] = self.wrapped

                def __getattr__(self, name):
                    return getattr(self.wrapped, name)
            # return class
            return Wrapper

        # return decorator
        return myfun

    def intent2(self, intentStr, **args):
        def myfun(cls):
            self.wrapped = cls
            self.intentActions[intentStr] = self.wrapped

            class Wrapper(object):
                def __init__(self, *args):
                    self.wrapped = cls
                    self.intentActions[intentStr] = self.wrapped
            # return class
            return Wrapper

        # return decorator
        return myfun

    def sendDebugResponse(self, botState, canonicalMsg):
        if self.debug:
            log.info("sending DEBUG info")
            try:
                self.createAndSendTextResponse(
                    canonicalMsg, "botState: %s" % (botState,),
                    messages.ResponseElement.RESPONSE_TYPE_DEBUG)
            except Exception as e:
                log.exception(e.message)
        else:
            log.info("self.debug: %s. NOT sending DEBUG info", self.debug)


    @classmethod
    def _createBotKey(cls, canonicalMsg, id):
        k = "%s.%s.%s.%s" % (
            cls.__name__, canonicalMsg.userId,
            canonicalMsg.channel, id)
        return k

    def createActionObject(self, canonicalMsg, apiResult, botState, userProfile, requestState):

        """
        Create a new action object from the given data
        canonicalMsg, apiResult, intentStr
        slots, messages, channelClient

        """
        # Get the intent string and create an object from it.
        intentStr = apiResult.intent.label
        actionObjectCls = self.intentActions.get(intentStr)
        log.debug("createActionObject: intent: %s cls: %s", intentStr, actionObjectCls)
        slotClasses = slot_fill.getSlots(actionObjectCls)
        slotObjects = []
        for slotClass in slotClasses:
            sc = slotClass()
            sc.entityType = getattr(sc, "entityType")
            sc.required = getattr(sc, "required")
            sc.parseOriginal = getattr(sc, "parseOriginal")
            sc.parseResponse = getattr(sc, "parseResponse")
            slotObjects.append(sc)
        actionObject = actionObjectCls()
        actionObject.slotObjects = slotObjects
        actionObject.apiResult = apiResult
        actionObject.canonicalMsg = canonicalMsg
        actionObject.channelClient = self.channelClient
        actionObject.requestState = requestState
        actionObject.originalIntentStr = intentStr
        log.debug("createActionObject: %s", actionObject)
        return actionObject

    def getActionObject(self, actionObjectJSON, canonicalMsg, apiResult, userProfile, requestState):
        """
        Create an action object from a given JSON object
        """
        # Initialize the class
        intentStr = actionObjectJSON.get("origIntentStr")
        slotObjectData = actionObjectJSON.get("slotObjects")
        actionObjectCls = self.intentActions.get(intentStr)
        actionObject = actionObjectCls()
        slotClasses = slot_fill.getSlots(actionObjectCls)
        slotObjects = []
        for slotClass, slotObject in zip(slotClasses, slotObjectData):
            sc = slotClass()
            sc.entityType = getattr(sc, "entityType")
            sc.required = getattr(sc, "required")
            sc.parseOriginal = getattr(sc, "parseOriginal")
            sc.parseResponse = getattr(sc, "parseResponse")
            # Get these from the saved state
            sc.filled = slotObject.get("filled")
            sc.value = slotObject.get("value")
            sc.validated = slotObject.get("validated")
            sc.state = slotObject.get("state")
            slotObjects.append(sc)

        actionObject.slotObjects = slotObjects
        actionObject.apiResult = apiResult
        actionObject.canonicalMsg = canonicalMsg
        actionObject.channelClient = self.channelClient
        actionObject.requestState = requestState
        actionObject.originalIntentStr = intentStr
        log.debug("createActionObject: %s", actionObject)
        return actionObject

    def process(self, canonicalMsg):

        botState = self.getBotState(
            userId=canonicalMsg.userId,
            channel=canonicalMsg.channel)

        userProfile = self.getUserProfile(
            userId=canonicalMsg.userId,
            channel=canonicalMsg.channel
        )

        return self.handle(
            canonicalMsg = canonicalMsg,
            myraAPI = self.api,
            botState = botState,
            userProfile = userProfile
        )

    def handle(self, **kwargs):

        """
        When the user creates a bot object, we initialize all the action objects needed
        in the interaction graph and initialize, and store.

        We then map these initialized objects into the hashmap which contains intents.

        For a given intent, this hashmap is what's used to determine which action object
        to invoke.

        Before we initialize the action object we check if there's a version already stored.
        If there isn't, then we do a new one, else we retrieve it from the old one.

        """

        canonicalMsg = kwargs.get("canonicalMsg")
        myraAPI = kwargs.get("myraAPI")
        apiResult = myraAPI.get(canonicalMsg.text)
        botState = kwargs.get("botState")
        userProfile = kwargs.get("userProfile")

        botState.setDebug(self.debug)

        requestState = BaseBot.REQUEST_STATE_NEW
        waitingActionJson = botState.getWaiting()

        if waitingActionJson:
            actionObject = self.getActionObject(waitingActionJson, canonicalMsg, apiResult, userProfile, requestState)
            #self.sendDebugResponse(botState, canonicalMsg)
            requestState = actionObject.processWrapper(botState)

        if requestState != BaseBot.REQUEST_STATE_PROCESSED:
            log.debug("requestState: %s", requestState)
            log.debug("botState: %s", botState)
            actionObject = self.createActionObject(
                canonicalMsg, apiResult, botState, userProfile, requestState)
            log.debug("actionObject: %s", actionObject)
            #self.sendDebugResponse(botState, canonicalMsg)
            requestState = actionObject.processWrapper(botState)
            log.debug("requeststate: %s", requestState)

        if requestState != BaseBot.REQUEST_STATE_PROCESSED:
            raise Exception("Unprocessed message")

        if botState.changed:
            self.putBotState(
                userId=canonicalMsg.userId,
                channel=canonicalMsg.channel,
                botState=botState
            )
        return requestState
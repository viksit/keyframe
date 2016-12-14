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
from orderedset import OrderedSet


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
        self.keywordIntentsList = {}
        self.regexIntents = {}

        self.intentEvalSet = OrderedSet([])

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


    def keyword_intent(self, intentStr, intentKeywordList, **args):
        def myfun(cls):
            self.wrapped = cls
            self.keywordIntents[intentStr] = self.wrapped
            self.keywordIntentsList[intentStr] = intentKeywordList

            class Wrapper(object):
                def __init__(self, *args):
                    self.wrapped = cls
                    self.keywordIntents[intentStr] = self.wrapped
                    self.keywordIntentsList[intentStr] = intentKeywordList
            # return class
            return Wrapper

        # return decorator
        return myfun

    def intent(self, intentStr, **args):
    def intent(self, intentObj, **args):
        """
        intent can be a string or also some variable.
        if its a var like modelclassname.varname
        we initialize that
        the resulting class should give us an
         - intent_name: this is the value of the var name
         - intent_type - this is the string key which will return.
         - intent_eval_fn - if this evaluates to true then we return the intent type
         - intent_register_fn - used to register this intent in our dict
        which we can run

        registration flow

        - find the class object, get its string
        - intentactionmap[string] = actionobject
        - intentevallist = [intentobject1, intentobject2]

        text flow

        - text comes in, we run a loop through all intent eval functions
        - evaluate them on this string and see if any match. first match is
          taken. return intenteval.label
        - this is then used to get intentactonmap.get(label)

        """
        def myfun(cls):
            self.wrapped = cls
            self.intentActions[intentObj.label] = self.wrapped
            self.intentEvalSet.add(intentObj)

            class Wrapper(object):
                def __init__(self, *args):
                    self.wrapped = cls
                    self.intentActions[intentObj.label] = self.wrapped
                    self.intentEvalSet.add(intentObj)
            # return class
            return Wrapper

        # return decorator
        return myfun

    def processMsg(self, canonicalMsg):
        """Extracts intent and entities as appropriate and
        returns them as ProcessedInputMsg.
        """
        # TODO: Need to know how to handle a mix of api and non-api
        # intent and entities.
        pim = messages.ProcessedInputMsg(None, None, None)
        intentStr = self.processKeywordIntent(canonicalMsg)
        if intentStr:
            pim.intent = intentStr
            pim.intentScore = 1
        elif self.intents:
            if not self.api:
                raise Exception(
                    ("intents without api! "
                     "You can't decorate your cake without icing."))
            apiResult = self.api.get(canonicalMsg.text)
            pim = self.apiResultToProcessedInputMsg(apiResult)
        else:
            pim = messages.ProcessedInputIntent(
                intent="unknown", intentScore=1, entities=None)
        return pim

    def apiResultToProcessedInputMsg(self, apiResult):
        """Transform apiResult into ProcessedInputMsg.
        """
        if not apiResult:
            return None
        pim = messages.ProcessedInputMsg(None, None, None)
        if apiResult.intent:
            pim.intent = apiResult.intent.label
            pim.intentScore = apiResult.intent.score
        pim.entities = apiResult.entities
        return pim
        
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

    def createActionObject(self, canonicalMsg, processedInputMsg, botState, userProfile, requestState):

        """
        Create a new action object from the given data
        canonicalMsg, processedInputMsg, intentStr
        slots, messages, channelClient

        """
        # Get the intent string and create an object from it.
        intentStr, actionObjectCls = self._getActionObjectFromIntentHandlers(canonicalMsg)
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
        actionObject.processedInputMsg = processedInputMsg
        actionObject.canonicalMsg = canonicalMsg
        actionObject.channelClient = self.channelClient
        actionObject.requestState = requestState
        actionObject.originalIntentStr = intentStr
        log.debug("createActionObject: %s", actionObject)
        return actionObject

    def getActionObject(self, actionObjectJSON, canonicalMsg, processedInputMsg, userProfile, requestState):
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
        actionObject.processedInputMsg = processedInputMsg
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
            botState = botState,
            userProfile = userProfile
        )

    def _getActionObjectFromIntentHandlers(self, canonicalMsg):
        # Support default intent.
        intentStr = "default"

        # For now, simply go through the list and return the first one that comes up.
        # In the future, we could do something different.
        # If no intents are matched we just return whatever is mapped to a default intent.

        for intentObj in self.intentEvalSet:
            if intentObj.field_eval_fn(
                    myraAPI = self.api,
                    canonicalMsg = canonicalMsg):
                intentStr = intentObj.label
                break

        # We now check if this intent has any registered action objects.
        actionObjectCls = self.intentActions.get(intentStr, None)

        assert actionObjectCls is not None, "No action objects were registered for this intent"
        return (intentStr, actionObjectCls)

    def _kwIntentMatch(self, text, keywordList):
        s1 = set(text.split())
        s2 = set(keywordList)
        return bool(set.intersection(s1, s2))

    def processKeywordIntent(self, canonicalMsg):
        # Loop through self,keywordintents
        # See if this word is within the sentence
        # if yes, return true, else false
        #for (k,v) in self.keywordIntentsList.iteritems():
        pass

    def _generateMockAPIResult(self):
        # Copy the format for the myra API response
        # send it across
        pass


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

        # TODO(viksit): Don't run API by default
        # We do this right now since we need apiresult in our main
        # slot fill function.
        # This should be controlled by APIEntity() or something.

        processedInputMsg = messages.ProcessedInputMsg(None, None, None)
        # TODO: Check if we have keyword intents. If yes call.
        intentStr = self.processKeywordIntent(canonicalMsg)
        if not processedInputMsg:
            # TODO: Check if we have an intent or entity model. If not, should be
            # the unknown intent.
            myraAPI = kwargs.get("myraAPI")
            if not myraAPI:
                processedInputMsg = messages.ProcessedInputIntent(
                    intent="unknown", intentScore=1, entities=None)
            else:
                apiResult = myraAPI.get(canonicalMsg.text)
                processedInputMsg = self.apiResultToProcessedInputMsg(apiResult)

        # Nishant: start here
        assert apiResult is not None


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

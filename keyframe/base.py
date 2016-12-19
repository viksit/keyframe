from __future__ import print_function
import logging

import messages
import slot_fill
import dsl
import copy
import misc
from collections import defaultdict
import sys
import utils
from bot_state import BotState
import actions
import constants

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

    # User profile keys
    UP_NAME = "up_name"

    def __init__(self, *args, **kwargs):
        self.name = kwargs.get("name")
        self.api = kwargs.get("api", None)
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

        self.intentEvalSet = OrderedSet([])

        self.intentSlots = defaultdict(lambda: [])
        self.debug = True


        self.init()

    def init(self):
        # Override to initialize stuff in derived bots
        pass

    # Bot state related functions

    def getUserProfile(self, userId, channel):

        userProfileKey = "%s.%s.userprofile.%s.%s" % (
            self.__class__.__name__, self.name, userId, channel)

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
        k = "botstate.%s.%s.%s.%s" % (
            self.__class__.__name__, self.name, userId, channel)
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


    # TODO: Looks like this is not used?
    @classmethod
    def _createBotKey(cls, canonicalMsg, id):
        k = "%s.%s.%s.%s" % (
            cls.__name__, canonicalMsg.userId,
            canonicalMsg.channel, id)
        return k

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

    def _getActionObjectFromIntentHandlers(self, canonicalMsg):

        # Support default intent.
        intentStr = "default"

        # For now, simply go through the list and return the first one that comes up.
        # In the future, we could do something different.
        # If no intents are matched we just return whatever is mapped to a default intent.

        defaultIntent = None
        for intentObj in self.intentEvalSet:
            log.debug("intentObj: %s", intentObj)
            if isinstance(intentObj, dsl.DefaultIntent):
                defaultIntent = intentObj
                continue
            if intentObj.field_eval_fn(
                    myraAPI = self.api, # If no API is passed to bot, this will be None
                    canonicalMsg = canonicalMsg):
                intentStr = intentObj.label
                log.debug("found intentStr: %s", intentStr)
                break
        # No non-default intent detected.
        if not intentStr and defaultIntent:
            intentStr = defaultIntent.label
        log.debug("intentStr: %s", intentStr)
        # We now check if this intent has any registered action objects.
        actionObjectCls = self.intentActions.get(intentStr, None)

        assert actionObjectCls is not None, "No action objects were registered for this intent"
        return (intentStr, actionObjectCls)

    def createActionObject(self, actionObjectCls, intentStr,
                           canonicalMsg, botState,
                           userProfile, requestState):
        return actionObjectCls.createActionObject(
            intentStr, canonicalMsg, botState,
            userProfile, requestState, self.api, self.channelClient)


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

        botState = kwargs.get("botState")
        userProfile = kwargs.get("userProfile")

        botState.setDebug(self.debug)

        requestState = constants.BOT_REQUEST_STATE_NEW
        waitingActionJson = botState.getWaiting()
        log.debug("waitingActionJson: %s", waitingActionJson)
        if waitingActionJson:
            intentStr = actions.ActionObject.getIntentStrFromJSON(waitingActionJson)
            actionObjectCls = self.intentActions.get(intentStr)
            actionObject = self.createActionObject(
                actionObjectCls, intentStr,
                canonicalMsg, botState, userProfile, requestState)
            actionObject.populateFromJson(waitingActionJson)
            #self.sendDebugResponse(botState, canonicalMsg)
            requestState = actionObject.processWrapper(botState)

        if requestState != constants.BOT_REQUEST_STATE_PROCESSED:
            log.debug("requestState: %s", requestState)
            log.debug("botState: %s", botState)
            intentStr, actionObjectCls = self._getActionObjectFromIntentHandlers(canonicalMsg)
            log.debug("GetActionObjectFromIntentHandlers: intent: %s cls: %s", intentStr, actionObjectCls)
            actionObject = self.createActionObject(
                actionObjectCls,
                intentStr, canonicalMsg, botState, userProfile,
                requestState)
            log.debug("actionObject: %s", actionObject)
            #self.sendDebugResponse(botState, canonicalMsg)
            requestState = actionObject.processWrapper(botState)
            log.debug("requeststate: %s", requestState)

        if requestState != constants.BOT_REQUEST_STATE_PROCESSED:
            raise Exception("Unprocessed message")

        if botState.changed:
            self.putBotState(
                userId=canonicalMsg.userId,
                channel=canonicalMsg.channel,
                botState=botState
            )
        return requestState

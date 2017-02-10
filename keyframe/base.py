from __future__ import print_function
import logging
import json
import re

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

# ordereset has a .so file which is incompat with lambda.
# from orderedset import OrderedSet
# alternative
from ordered_set import OrderedSet


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
        log.debug("BaseBot: returning botstate key: %s", k)
        return k

    def getBotState(self, userId, channel):
        log.debug("getBotState(%s)", locals())
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

    debug_intent_re = re.compile("\[intent=([^\]]+)\]")
    def _getDebugActionObject(self, canonicalMsg):
        log.debug("_getDebugActionObject called")
        utterance = canonicalMsg.text
        if not utterance:
            return None
        x = self.debug_intent_re.match(utterance)
        if not x:
            return None
        intentStr = x.groups()[0]
        actionObjectCls = self.intentActions.get(intentStr)
        assert actionObjectCls, "No action object for intent: %s" % (intentStr,)
        d = {"intentStr":intentStr, "intentScore":1,
                "actionObjectCls":actionObjectCls}
        log.debug("RETURNING DEBUG action: %s", d)
        return d

    def _getActionObjectFromIntentHandlers(self, canonicalMsg):

        # Support default intent.
        intentStr = "default"

        # For now, simply go through the list and return the first one that comes up.
        # In the future, we could do something different.
        # If no intents are matched we just return whatever is mapped to a default intent.
        apiResult = None
        intentScore = 1
        defaultIntent = None
        # debug
        r = self._getDebugActionObject(canonicalMsg)
        if r:
            return (r["intentStr"], r.get("intentScore",1),
                    r["actionObjectCls"], r.get("apiResult"))

        for intentObj in self.intentEvalSet:
            log.debug("intentObj: %s", intentObj)
            if isinstance(intentObj, dsl.DefaultIntent):
                defaultIntent = intentObj
                continue
            evalRet = intentObj.field_eval_fn(
                myraAPI = self.api, # If no API is passed to bot, this will be None
                canonicalMsg = canonicalMsg,
                apiResult = apiResult)
            apiResult = evalRet.get("api_result")
            if evalRet["result"]:
                intentStr = intentObj.label
                log.debug("found intentStr: %s", intentStr)
                log.debug("api Result: %s", apiResult)
                intentScore = evalRet.get("score", intentScore)
                break
        # No non-default intent detected.
        if not intentStr and defaultIntent:
            intentStr = defaultIntent.label
        log.debug("intentStr: %s", intentStr)
        # We now check if this intent has any registered action objects.
        actionObjectCls = self.intentActions.get(intentStr, None)
        assert actionObjectCls is not None, "No action objects were registered for this intent"
        return (intentStr, intentScore, actionObjectCls, apiResult)

    def createActionObject(self, actionObjectCls, intentStr,
                           canonicalMsg, botState,
                           userProfile, requestState,
                           apiResult=None, newIntent=None):
        log.debug("BaseBot.createActionObject(%s)", locals())
        return actionObjectCls.createActionObject(
            intentStr, canonicalMsg, botState,
            userProfile, requestState, self.api, self.channelClient,
            apiResult=apiResult, newIntent=newIntent)


    def _handleBotCmd(self, canonicalMsg, botState, userProfile, requestState):
        msg = canonicalMsg.text.lower()
        respText = "This command wasn't found"
        if msg.startswith("botcmd help"):
            helpMsg = "botcmd <clear/show> <profile/state>"
            respText = helpMsg

        if msg.find("clear profile") > -1:
            userProfile.clear()
            respText = "user profile has been cleared"

        if msg.find("show state") > -1:
            botState = self.getBotState(
                userId=canonicalMsg.userId,
                channel=canonicalMsg.channel)
            respText = botState.toJSONObject()

        if msg.find("clear state") > -1:
            botState = self.getBotState(
                userId=canonicalMsg.userId,
                channel=canonicalMsg.channel)
            log.debug("botstate pre: %s", botState)
            botState.clear()
            self.putBotState(
                userId=canonicalMsg.userId,
                channel=canonicalMsg.channel,
                botState=self.botStateClass()
            )
            log.debug("botstate post: %s", botState)
            respText = "bot state has been cleared"

        self.createAndSendTextResponse(
            canonicalMsg,
            respText,
            messages.ResponseElement.RESPONSE_TYPE_RESPONSE)
        return constants.BOT_REQUEST_STATE_PROCESSED


    def handle(self, **kwargs):

        """
        When the user creates a bot object, we initialize all the action objects needed
        in the interaction graph and initialize, and store.

        We then map these initialized objects into the hashmap which contains intents.

        For a given intent, this hashmap is what's used to determine which action object
        to invoke.

        Before we initialize the action object we check if there's a version already stored.
        If there isn't, then we do a new one, else we retrieve it from the old one.

        If we see botcmd, then handle as a botcmd action rather than going through intent/keyword
        action.

        """
        canonicalMsg = kwargs.get("canonicalMsg")
        botState = kwargs.get("botState")
        userProfile = kwargs.get("userProfile")

        log.debug("userProfile: %s", userProfile)
        botState.setDebug(self.debug)
        requestState = constants.BOT_REQUEST_STATE_NEW

        # Check for a bot command
        msg = canonicalMsg.text.lower()
        if msg.startswith("botcmd"):
            requestState = self._handleBotCmd(canonicalMsg, botState, userProfile, requestState)
            if requestState == constants.BOT_REQUEST_STATE_PROCESSED:
                return

        intentStr, intentScore, actionObjectCls, apiResult = self._getActionObjectFromIntentHandlers(canonicalMsg)
        log.debug("GetActionObjectFromIntentHandlers: intent: %s cls: %s", intentStr, actionObjectCls)
        preemptWaitingAction = False
        intentActionObject = self.createActionObject(
            actionObjectCls,
            intentStr, canonicalMsg, botState, userProfile,
            requestState, apiResult=apiResult, newIntent=True)
        log.debug("intentActionObject: %s", intentActionObject)
        preemptThreshold = intentActionObject.getPreemptWaitingActionThreshold()
        if preemptThreshold and float(preemptThreshold) <= intentScore:
            preemptWaitingAction = True

        if not preemptWaitingAction:
            waitingActionJson = botState.getWaiting()
            log.debug("waitingActionJson: %s", waitingActionJson)
            if waitingActionJson:
                intentStr = actions.ActionObject.getIntentStrFromJSON(waitingActionJson)
                actionObjectCls = self.intentActions.get(intentStr)
                waitingActionObject = self.createActionObject(
                    actionObjectCls, intentStr,
                    canonicalMsg, botState, userProfile,
                    requestState, newIntent=False)
                waitingActionObject.populateFromJson(waitingActionJson)
                #self.sendDebugResponse(botState, canonicalMsg)
                requestState = waitingActionObject.processWrapper(botState)

        if requestState != constants.BOT_REQUEST_STATE_PROCESSED:
            log.debug("requestState: %s", requestState)
            log.debug("botState: %s", botState)
            #self.sendDebugResponse(botState, canonicalMsg)
            requestState = intentActionObject.processWrapper(botState)
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

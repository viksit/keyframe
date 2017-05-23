from __future__ import print_function
import logging
import json
import re
import copy
import time

import messages
import slot_fill
import dsl
import config
import misc
from collections import defaultdict
import sys
import utils
from bot_state import BotState
import actions
import constants
import event
import event_writer

from six import iteritems, add_metaclass

# ordereset has a .so file which is incompat with lambda.
# from orderedset import OrderedSet
# alternative
from ordered_set import OrderedSet


# TODO: move logging out into a nicer function/module

log = logging.getLogger(__name__)
#log.setLevel(10)

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
        if not self.config:
            self.config = config.getConfig()
        self.debug = kwargs.get("debug")

        # self.slotFill = slot_fill.SlotFill()

        #self.topicActions = {}
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

    def _botStateHistoryKey(self, userId, channel, botStateUid):
        log.debug("_botStateHistoryKey(%s)", locals())
        k = self._botStateKey(userId, channel)
        k = "history." + k + "." + botStateUid
        log.debug("BaseBot._botStateHistoryKey returning: %s", k)
        return k

    def getBotState(self, userId, channel, botStateUid=None):
        log.debug("getBotState(%s)", locals())
        k = self._botStateKey(userId, channel)
        if botStateUid:
            k = self._botStateHistoryKey(userId, channel, botStateUid)
        jsonObject = self.kvStore.get_json(k)
        if not jsonObject:
            assert not botStateUid, "Could not get botStateUid: %s (key: %s)" % (
                botStateUid, k)
            return self.botStateClass()
        return self.botStateClass.fromJSONObject(jsonObject)

    def putBotState(self, userId, channel, botState, botStateUid):
        #log.debug("putBotState(%s)", locals())
        k = self._botStateKey(userId, channel)
        botState.setWriteTime(time.time())
        botStateJson = botState.toJSONObject()
        self.kvStore.put_json(k, botState.toJSONObject())
        # Always also add to history.
        if botStateUid:
            self.putBotStateHistory(userId, channel, botState, botStateUid)

    def putBotStateHistory(self, userId, channel, botState, botStateUid):
        k = self._botStateHistoryKey(userId, channel, botStateUid)
        expiry_time = int(time.time()) + self.config.BOTSTATE_HISTORY_TTL_SECONDS
        self.kvStore.put_json(k, botState.toJSONObject(),
                              expiry_time=expiry_time)

    # Channel and I/O related functions
    def setChannelClient(self, cc):
        self.channelClient = cc


    def createAndSendTextResponse(self, canonicalMsg, text, responseType=None,
                                  botStateUid=None):
        log.info("createAndSendTextResponse(%s)", locals())
        cr = messages.createTextResponse(
            canonicalMsg, text, responseType,
            botStateUid=botStateUid)
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
                    messages.ResponseElement.RESPONSE_TYPE_DEBUG,
                    botStateUid=botState.getUid())
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
            channel=canonicalMsg.channel,
            botStateUid=canonicalMsg.botStateUid)
        
        # self.putBotStateHistory(
        #     userId=canonicalMsg.userId,
        #     channel=canonicalMsg.channel,
        #     botState=botState,
        #     uid=botStateUid)

        # create a state uid so we can keep track of botstate.
        newBotStateUid = utils.timestampUid()
        log.info("newBotStateUid: %s", newBotStateUid)
        botState.shiftUid(newBotStateUid)
        #canonicalMsg.botStateUid = botStateUid

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

    def createActionObject(self, accountId, agentId, topicId,
                           canonicalMsg, botState,
                           userProfile, requestState,
                           apiResult=None, newTopic=None):
        log.debug("BaseBot.createActionObject(%s)", locals())
        return actions.ActionObject.createActionObject(
            accountId, agentId,
            topicId,
            canonicalMsg, botState,
            userProfile, requestState, self.api, self.channelClient,
            apiResult=apiResult, newIntent=newIntent)

    def _handleBotCmd(self, canonicalMsg, botState, userProfile, requestState):
        log.debug("_handleBotCmd called")
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
            botState.clear()
            # Don't start a user session on botcmd clear state!
            self.putBotState(
                userId=canonicalMsg.userId,
                channel=canonicalMsg.channel,
                #botState=self.botStateClass(),
                botState=botState,
                botStateUid=botState.getUid()
            )
            log.debug("botstate post: %s", botState)
            respText = "bot state has been cleared"

        self.createAndSendTextResponse(
            canonicalMsg,
            respText,
            messages.ResponseElement.RESPONSE_TYPE_RESPONSE,
            botStateUid=botState.getUid())
        return constants.BOT_REQUEST_STATE_PROCESSED

    topic_re = re.compile("\[topic=([^\]]+)\]")
    def handle(self, **kwargs):
        log.debug("BaseBot.handle(%s)", locals())
        canonicalMsg = kwargs.get("canonicalMsg")
        botState = kwargs.get("botState")
        userProfile = kwargs.get("userProfile")

        log.debug("userProfile: %s", userProfile)
        botState.setDebug(self.debug)
        requestState = constants.BOT_REQUEST_STATE_NEW

        # Check for a bot command
        msg = canonicalMsg.text.lower()
        log.debug("checking for botcmd (%s)", msg)
        if msg.startswith("botcmd"):
            requestState = self._handleBotCmd(canonicalMsg, botState, userProfile, requestState)
            if requestState == constants.BOT_REQUEST_STATE_PROCESSED:
                return
        else:
            log.debug("not a botcmd")

        transferTopicId = None
        newSession = False

        wroteEvent = False

        while True:
            topicId = None
            actionStateJson = None
            newTopic = None

            # check for [topic=xxxx]
            x = self.topic_re.match(canonicalMsg.text.lower())
            if x:
                tmp1 = x.groups()[0].lower()
                if tmp1 == "default":
                    topicId = self.getStartTopic()
                    newTopic = True
                else:
                    topicId = tmp1
                    newTopic = True
                botState.clear()
                botState.startSession(canonicalMsg.userId)
                newSession = True
                canonicalMsg.text = canonicalMsg.text.replace(x.group(), "")

            if not topicId:
                if transferTopicId:
                    topicId = transferTopicId
                    transferTopicId = None
                    newTopic = True
                    # TODO(now): For a non (diagnostic -> resolution) transfer,
                    # botState.clear() should probably be called!
                else:
                    actionStateJson = botState.getWaiting()
                    newTopic = False
                    log.debug("actionJson: %s", actionStateJson)
                    if actionStateJson:
                        lastWriteTime = botState.getWriteTime()
                        currentTime = time.time()
                        log.debug("lastWriteTime: %s, currentTime: %s",
                                  lastWriteTime, currentTime)
                        if lastWriteTime and lastWriteTime > currentTime - self.config.BOTSTATE_TTL_SECONDS: 
                            topicId = actionStateJson.get("origTopicId")
                        else:
                            log.debug("SESSION TIMED OUT")
                            cr = messages.createTextResponse(
                                canonicalMsg,
                                "Your session has timed out.",
                                messages.ResponseElement.RESPONSE_TYPE_RESPONSE,
                                #botStateUid=botState.getUid(),
                                inputExpected=False)
                            self.channelClient.sendResponse(cr)
                            canonicalMsg.text = ""
                            botState.clear()
                            actionStateJson = None

            if not topicId:
                topicId = self.getStartTopic()
                log.debug("got START topic: %s", topicId)
                newTopic = True
                botState.clear()
                botState.startSession(canonicalMsg.userId)
                newSession = True

            # Now we should have a topicId
            actionObject = self.createActionObject(
                self.accountId, self.agentId,
                topicId,
                canonicalMsg, botState, userProfile,
                requestState, newTopic=newTopic)
            if actionStateJson:
                actionObject.fromJSONObject(actionStateJson)

            sessionStatus = None
            if newSession:
                sessionStatus = "start"

            # Only write the request event once.
            if not wroteEvent:
                requestEvent = event.createEvent(
                    accountId=self.accountId,
                    agentId=self.agentId,
                    eventType="request", src="user",
                    sessionStatus=sessionStatus,
                    sessionId=botState.getSessionId(),
                    userId=canonicalMsg.userId,
                    topicId=topicId,
                    topicType=actionObject.getTopicType(),
                    payload=canonicalMsg.toJSON())
                eventWriter = event_writer.getWriter()
                eventWriter.write(requestEvent.toJSONStr(), requestEvent.userId)
                wroteEvent = True

            requestState = actionObject.processWrapper(botState)
            log.debug("requestState: %s", requestState)
            if requestState == constants.BOT_REQUEST_STATE_PROCESSED:
                break
            if requestState == constants.BOT_REQUEST_STATE_TRANSFER:
                transferTopicId = botState.getTransferTopicId()

        if botState.changed:
            self.putBotState(
                userId=canonicalMsg.userId,
                channel=canonicalMsg.channel,
                botState=botState,
                botStateUid=botState.getUid()
            )
        return requestState


    def getStartActionObject(
            self, canonicalMsg, botState, userProfile, requestState):
        # TODO(now)
        raise NotImplementedError()


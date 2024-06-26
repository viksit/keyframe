from __future__ import print_function
from __future__ import absolute_import
import logging
import json
import re
import copy
import time
import requests
import requests.exceptions

from . import messages
from . import slot_fill
from . import dsl
from . import config
from . import misc
from collections import defaultdict
import sys
from . import utils
from .bot_state import BotState
from . import actions
from . import constants
from . import event
from . import event_writer

from six import iteritems, add_metaclass

# ordereset has a .so file which is incompat with lambda.
# from orderedset import OrderedSet
# alternative
from ordered_set import OrderedSet
import six


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

    def getUserProfile(self, userId, channel):
        return None

    # Bot state related functions
    def getUserProfileNotNeededYet(self, userId, channel):

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

    def _botStateKey(self, userId, channel, instanceId):
        k = "botstate.%s.%s.%s.%s.%s" % (
            self.__class__.__name__, self.name, userId, channel, instanceId)
        log.debug("BaseBot: returning botstate key: %s", k)
        return k

    def _botStateHistoryKey(self, userId, channel, instanceId, botStateUid):
        log.debug("_botStateHistoryKey(%s)", locals())
        k = self._botStateKey(userId, channel, instanceId)
        k = "history." + k + "." + botStateUid
        log.debug("BaseBot._botStateHistoryKey returning: %s", k)
        return k

    def getBotState(self, userId, channel, instanceId, botStateUid=None):
        log.info("getBotState(%s)", locals())
        k = self._botStateKey(userId, channel, instanceId)
        log.info("botstatekey: %s", k)
        if botStateUid:
            k = self._botStateHistoryKey(userId, channel, instanceId, botStateUid)
        jsonObject = self.kvStore.get_json(k)
        if not jsonObject:
            assert not botStateUid, "Could not get botStateUid: %s (key: %s)" % (
                botStateUid, k)
            return self.botStateClass()
        return self.botStateClass.fromJSONObject(jsonObject)

    def putBotState(self, userId, channel, instanceId, botState, botStateUid):
        #log.debug("putBotState(%s)", locals())
        k = self._botStateKey(userId, channel, instanceId)
        botState.setWriteTime(time.time())
        botStateJson = botState.toJSONObject()
        self.kvStore.put_json(k, botState.toJSONObject())
        # For now, disable history until we need it.
        if botStateUid: #  and False:
            self.putBotStateHistory(
                userId, channel, instanceId, botState, botStateUid)

    def putBotStateHistory(self, userId, channel,
                           instanceId, botState, botStateUid):
        k = self._botStateHistoryKey(userId, channel, instanceId, botStateUid)
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
        log.info("BaseBot::process(%s)", canonicalMsg.text)
        botState = self.getBotState(
            userId=canonicalMsg.userId,
            channel=canonicalMsg.channel,
            instanceId=canonicalMsg.instanceId,
            botStateUid=canonicalMsg.botStateUid)

        if canonicalMsg.msgType == messages.CanonicalMsg.MSG_TYPE_EVENT:
            return self.handleEvent(
                canonicalMsg=canonicalMsg, botState=botState)
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

    def handleEvent(self, canonicalMsg, botState):
        log.info("handleEvent(%s)", locals())
        #time.sleep(20)  # For testing widget event generation async...
        e = canonicalMsg.eventInfo
        sessionStatus = None
        createNewSession = False

        if not (botState or botState.getSessionId()):
            createNewSession = True

        if not createNewSession:
            lastWriteTime = botState.getWriteTime()
            currentTime = time.time()
            log.debug("lastWriteTime: %s, currentTime: %s",
                      lastWriteTime, currentTime)
            if lastWriteTime and lastWriteTime <= currentTime - self.config.BOTSTATE_TTL_SECONDS:
                createNewSession = True
                log.debug("SESSION TIMED OUT")
                cr = messages.createTextResponse(
                    canonicalMsg,
                    "Your session has timed out.",
                    messages.ResponseElement.RESPONSE_TYPE_RESPONSE,
                    #botStateUid=botState.getUid(),
                    inputExpected=False)
                self.channelClient.sendResponse(cr)

        if createNewSession:
            # There is no session. Create a new session.
            botState.clear()
            botState.startSession(
                canonicalMsg.userId, sessionProps={"location_href":canonicalMsg.locationHref})
            botState.sessionStartLastEvent = True
            sessionStatus = "start"
            self.putBotState(
                userId=canonicalMsg.userId,
                channel=canonicalMsg.channel,
                instanceId=canonicalMsg.instanceId,
                botState=botState,
                botStateUid=botState.getUid()
            )
        aEvent = event.createEvent(
            accountId=self.accountId,
            agentId=self.agentId,
            userId=canonicalMsg.userId,
            sessionStatus=sessionStatus,
            eventType=e.get("event_type"),
            sessionId=botState.getSessionId(),
            payload=e,
            customProps=canonicalMsg.customProps
        )

        eventWriter = event_writer.getWriter(
            streamName=self.config.KINESIS_STREAM_NAME)
        eventWriter.write(aEvent.toJSONStr(), canonicalMsg.userId)
        return constants.BOT_REQUEST_STATE_PROCESSED


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
                           apiResult=None, newTopic=None, topicNodeId=None,
                           config=None):
        log.info("createActionObject called")
        log.debug("BaseBot.createActionObject(%s)", locals())
        return actions.ActionObject.createActionObject(
            accountId, agentId,
            topicId,
            canonicalMsg, botState,
            userProfile, requestState, self.api, self.channelClient,
            apiResult=apiResult, newIntent=newIntent, config=config)

    @classmethod
    def _modelWarmUp(cls, modelId, config, timout=0.1):
        # Note that anything less than 0.1 seems to result in different exceptions
        # from the requests module.
        log.info("_modelWarmUp(%s)", locals())
        requestUrl = config.MYRA_SEARCH_SERVER
        # hack.
        if requestUrl.startswith("localhost"):
            requestUrl = "http://%s" % (requestUrl,)
        else:
            requestUrl = "https://%s" % (requestUrl,)
        requestUrl += "/%s?q=model%%20warmup%%20%s&model_id=%s" % (
            config.MYRA_SEARCH_ENDPOINT, time.time(), modelId)
        log.info("requestUrl: %s", requestUrl)
        try:
            requests.get(requestUrl, timeout=0.1)
        except requests.exceptions.ReadTimeout as rt:
            log.info("got expected readtimeout in model warming")
        except:
            log.exception("Got unexpected exception in model warming")
            # Lets swallow this one so that everything doesn't break because
            # there is a problem with calling inference proxy. Agents should not
            # break because of problems with inference_proxy (even if they have model_ids)

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
                channel=canonicalMsg.channel,
                instanceId=canonicalMsg.instanceId)
            respText = json.dumps(botState.toJSONObject())

        if msg.find("clear state") > -1:
            botState.clear()
            # Don't start a user session on botcmd clear state!
            self.putBotState(
                userId=canonicalMsg.userId,
                channel=canonicalMsg.channel,
                instanceId=canonicalMsg.instanceId,
                #botState=self.botStateClass(),
                botState=botState,
                botStateUid=botState.getUid()
            )
            log.debug("botstate post: %s", botState)
            respText = "bot state has been cleared"

            # Not sure where the best place to warm a model is. This will do.
            #nvsmIndex = self.specJson.get("params", {}).get("nvsm_index_for_workflows")
            # Above does not work if specJson has params set to None.
            _params = self.specJson.get("params")
            if _params:
                nvsmIndex = _params.get("nvsm_index_for_workflows")
                if nvsmIndex:
                    self._modelWarmUp(nvsmIndex, self.config)


        self.createAndSendTextResponse(
            canonicalMsg,
            respText,
            messages.ResponseElement.RESPONSE_TYPE_RESPONSE,
            botStateUid=botState.getUid())
        return constants.BOT_REQUEST_STATE_PROCESSED

    def _addCustomPropsToSession(self, customProps, botState):
        log.debug("BaseBot._addCustomPropsToSession: customProps: %s", customProps)
        if not customProps:
            return
        for (k,v) in six.iteritems(customProps):
            #botState.addToSessionData(k, v)  # No
            # Session data is only for entities (nodes). customProps will be available
            # as customprops as a separate dict (see Slot._entitiesDict.
            botState.addToSessionData("custom_props_%s" % (k,), v)


    topic_re = re.compile("\[topic=([^\]]+)\]")
    transfer_topic_re = re.compile("\[transfer-topic=([^\]]+)\]")
    def handle(self, **kwargs):
        log.info("BaseBot.handle called")
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
                return  # requestState
        else:
            log.debug("not a botcmd")

        transferTopicInfo = None
        newSession = False

        wroteEvent = False

        while True:
            log.info("botState.sessionStartLastEvent: %s", botState.sessionStartLastEvent)
            topicId = None
            topicNodeId = None
            actionStateJson = None
            newTopic = None

            # check for [topic=xxxx]
            xt = False
            x = self.transfer_topic_re.search(canonicalMsg.text.lower())
            if x:
                log.info("found transfer topic")
                xt = True
            if not x:
                # Sometimes there may be '[topic=default] [topic=xxxx]'  (intercom app)
                # take the last one.
                _tmp = self.topic_re.finditer(canonicalMsg.text.lower())
                _tmp = [e for e in _tmp]
                if _tmp:
                    x = _tmp[-1]

            if x:
                tmp1 = x.groups()[0].lower()
                if tmp1 == "default":
                    topicId = self.getStartTopic()
                    newTopic = True
                else:
                    topicId = tmp1
                    newTopic = True
                # This is a manual command. Don't clear state.
                # If user wants to clear state, they can also do that manually.
                #botState.clear()
                if not xt:
                    # Special case for not starting a new session.
                    if botState.sessionStartLastEvent:
                        log.info("NOT starting new session and setting sessionStartLastEvent to False")
                        botState.sessionStartLastEvent = False
                        botState.changed = True
                        # Any subsequent [topic=xxx] commands will start a new session.
                    else:
                        log.info("starting new session")
                        botState.startSession(
                            canonicalMsg.userId, sessionProps={"location_href":canonicalMsg.locationHref})
                        #self._addCustomPropsToSession(
                        #    canonicalMsg.customProps, botState)
                        newSession = True
                canonicalMsg.text = canonicalMsg.text.lower().replace(x.group(), "")
                # Get rid of all [topic=xxx] from canonicalMsg.text
                _tmp = self.topic_re.finditer(canonicalMsg.text)
                for e in _tmp:
                    canonicalMsg.text = canonicalMsg.text.lower().replace(e.group(), "")
                log.info("final canonicalMsg.text: %s", canonicalMsg.text)

            if not topicId:
                if transferTopicInfo:
                    _d = transferTopicInfo
                    topicId = _d["transferTopicId"]
                    topicNodeId = _d["transferTopicNodeId"]
                    startNewSession = _d.get("startNewSession", False)
                    if startNewSession:
                        botState.clear()
                        botState.startSession(
                            canonicalMsg.userId, sessionProps={"location_href":canonicalMsg.locationHref})
                        newSession = True
                    transferTopicInfo = None
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
                        log.info("lastWriteTime: %s, currentTime: %s",
                                  lastWriteTime, currentTime)
                        if lastWriteTime and lastWriteTime > currentTime - self.config.BOTSTATE_TTL_SECONDS:
                            topicId = actionStateJson.get("origTopicId")
                        else:
                            log.info("SESSION TIMED OUT")
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
                botState.startSession(
                    canonicalMsg.userId, sessionProps={"location_href":canonicalMsg.locationHref})
                newSession = True

            # Any time custom props are passed in, add them to the session.
            self._addCustomPropsToSession(
                canonicalMsg.customProps, botState)

            # Now we should have a topicId
            actionObject = self.createActionObject(
                self.accountId, self.agentId,
                topicId,
                canonicalMsg, botState, userProfile,
                requestState, newTopic=newTopic, topicNodeId=topicNodeId,
                config=self.config)
            log.info("created actionObject")
            if actionStateJson:
                actionObject.fromJSONObject(actionStateJson)
                log.info("added actionStateJson")

            sessionStatus = None
            if newSession:
                sessionStatus = "start"

            log.info("sessionStatus: %s", sessionStatus)

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
                    payload=canonicalMsg.toJSON(),
                    locationHref=canonicalMsg.locationHref,
                    userInfo=canonicalMsg.userInfo,
                    workflowType=actionObject.getWorkflowType(),
                    customProps=canonicalMsg.customProps
                )
                eventWriter = event_writer.getWriter(
                    streamName=self.config.KINESIS_STREAM_NAME)
                eventWriter.write(requestEvent.toJSONStr(), requestEvent.userId)
                wroteEvent = True

            # If new topic, send new topic msg.
            if newTopic:
                newTopicResponse = messages.createNewTopicResponse(
                    canonicalMsg=canonicalMsg,
                    screenId=actionObject.screenId,
                    responseMeta=messages.ResponseMeta(
                        newTopic=newTopic, topicId=topicId),
                    botStateUid=botState.getUid())
                self.channelClient.sendResponse(newTopicResponse)

            requestState = actionObject.processWrapper(botState)
            log.info("requestState: %s", requestState)

            if requestState == constants.BOT_REQUEST_STATE_PROCESSED:
                break
            if requestState == constants.BOT_REQUEST_STATE_TRANSFER:
                transferTopicInfo = botState.getTransferTopicInfo()

        if botState.changed:
            self.putBotState(
                userId=canonicalMsg.userId,
                channel=canonicalMsg.channel,
                instanceId=canonicalMsg.instanceId,
                botState=botState,
                botStateUid=botState.getUid()
            )
        return requestState


    def getStartActionObject(
            self, canonicalMsg, botState, userProfile, requestState):
        # TODO(now)
        raise NotImplementedError()

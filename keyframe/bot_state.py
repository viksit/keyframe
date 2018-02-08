import time
import random
import logging

import messages
import channel_client
import fb
import config
import slot_fill
import copy
import bot_api
import store_api
from pymyra.api.messages import InferenceResult

log = logging.getLogger(__name__)

class BotState(object):

    """Serializable object for keeping bot state across requests.
    """

    def __init__(self):
        self.init(keepUid=False)
        #self.init()

    def init(self, keepUid=True):
        self._waiting = None
        # Json-compatible structure that allows
        self._lastResult = None  # CanonicalResult
        self.changed = False
        self.debug = False
        self.transferTopicInfo = None
        self._sessionData = {}
        self._sessionDataType = {}
        self._sessionUtterances = {}
        self._sessionUtterancesOrdered = []
        self._sessionUtterancesType = {}
        self._sessionUtterancesPrompt = {}
        self._sessionApiResults = {}
        self.sessionIntent = None
        self.sessionStartTime = None
        self.sessionId = None
        self.writeTime = None
        if not keepUid:
            self.uid = None
            self.previousUid = None

    def _createSessionId(self, userId, ts):
        return "kf_ses_%i_%s" % (ts, random.randint(0,1000))

    def startSession(self, userId, ts=None):
        self.clear()
        if not ts:
            ts = round(time.time()*1000)
        self.sessionStartTime = ts
        self.sessionId = self._createSessionId(userId, ts)
        self.changed = True

    def getSessionId(self):
        return self.sessionId

    def getSessionStartTime(self):
        return self.sessionStartTime

    def setSessionStartTime(self, t):
        # as a float seconds from epoch. (time.time())
        self.sessionStartTime = t

    def getWriteTime(self):
        return self.writeTime

    def setWriteTime(self, t):
        # as a float seconds from epoch. (time.time())
        self.writeTime = t

    def setSessionIntent(self, intentStr):
        self.sessionIntent = intentStr

    def getSessionIntent(self):
        return self.sessionIntent

    def getSessionData(self):
        return self._sessionData

    def getSessionApiResults(self):
        return self._sessionApiResults

    def getSessionDataType(self):
        return self._sessionDataType

    def getSessionUtterances(self):
        return self._sessionUtterances

    def getSessionUtterancesPrompt(self):
        return self._sessionUtterancesPrompt

    def getSessionUtterancesOrdered(self):
        #log.debug("getSessionUtterancesOrdered: %s", self._sessionUtterancesOrdered)
        return self._sessionUtterancesOrdered

    def getSessionUtterancesType(self):
        return self._sessionUtterancesType

    def getSessionDataType(self):
        return self._sessionDataType

    def addToSessionData(self, k, v, type=None):
        self._sessionData[k] = v
        self._sessionDataType[k] = type

    def addToSessionUtterances(self, k, v, p, type=None):
        #log.debug("existing SessionUtterancesOrdered: %s", self._sessionUtterancesOrdered)
        #log.debug("addToSessionUtterances(%s)", locals())
        self._sessionUtterances[k] = v
        self._sessionUtterancesPrompt[k] = p
        self._sessionUtterancesType[k] = type
        self._sessionUtterancesOrdered.append((k, v))

    def addToSessionApiResults(self, k, v):
        self._sessionApiResults[k] = v

    def getSessionTranscript(self):
        t = []
        for (k,v) in self._sessionUtterancesOrdered:
            d = {
                "slotname":k,
                "prompt":self._sessionUtterancesPrompt[k],
                "response":v
                }
            t.append(d)
        return t

    def getSessionDataType(self):
        return self._sessionDataType

    def getSessionDataElement(self, k):
        return {"value":self._sessionData.get(k),
                "type":self._sessionDataType.get(k)}

    def clearSessionXXX(self):
        self._sessionData = {}
        self._sessionUtterances = {}
        self._sessionUtterancesPrompt = {}
        self._sessionDataType = {}
        self._sessionUtterancesType = {}
        self.transferTopicInfo = None
        self.clearWaiting()

    def getTransferTopicInfo(self):
        return self.transferTopicInfo

    def setTransferTopicInfo(self, ttInfo):
        self.transferTopicInfo = ttInfo

    def setUid(self, uid):
        self.uid = uid

    def getUid(self):
        # What if it is None?
        return self.uid

    def setPreviousUid(self, previousUid):
        self.previousUid = previousUid

    def getPreviousUid(self):
        return self.previousUid

    def shiftUid(self, newUid):
        self.previousUid = self.uid
        self.uid = newUid

    def __repr__(self):
        return "%s" % (self.toJSONObject())

    def setDebug(self, debug):
        self.debug = debug

    def clear(self):
        self.init()
        self.changed = True

    def clearWaiting(self):
        if self._waiting:
            self._waiting = None
            self.changed = True

    def getWaiting(self):
        """Get an action object waiting for input, remove it
        from waiting, and return it (like a pop except this is not a stack).
        """
        if not self._waiting:
            return None
        tmp = self._waiting
        self._waiting = None
        self.changed = True
        return tmp

    def putWaiting(self, actionObjectJson):
        """Input
        actionObjectJson: (object) A json-compatible python data structure
        """
        self._waiting = actionObjectJson
        self.changed = True

    def getLastResult(self):
        return self._lastResult

    def putLastResult(self, canonicalResult):
        self._lastResult = canonicalResult
        self.changed = True

    def toJSONObject(self):
        """Return a json-compatible data structure with all of the
        data required to reconstruct this instance.
        """
        sessionApiResultsJson = {}
        for (k, v) in self._sessionApiResults.iteritems():
            sessionApiResultsJson[k] = v.toJSON()
        return {
            "class":self.__class__.__name__,
            "waiting":self._waiting,
            "last_result": self._lastResult,
            "uid": self.uid,
            "previous_uid": self.previousUid,
            "session_data": self._sessionData,
            "session_data_type": self._sessionDataType,
            "session_utterances": self._sessionUtterances,
            "session_utterances_type": self._sessionUtterancesType,
            "session_utterances_ordered":self._sessionUtterancesOrdered,
            "session_utterances_prompt": self._sessionUtterancesPrompt,
            "session_api_results": sessionApiResultsJson,
            "write_time":self.writeTime,
            "session_intent":self.sessionIntent,
            "session_id":self.sessionId,
            "session_start_time":self.sessionStartTime
        }

    @classmethod
    def fromJSONObject(cls, jsonObject):
        """Input
        jsonObject: object as returned by toJSONObject()
        """
        assert jsonObject.get("class") == cls.__name__, \
            "bad class. data class: %s, my class: %s" % (
                jsonObject.get("class"), cls.__name__)
        botState = cls()
        botState._waiting = jsonObject.get("waiting")
        botState._lastResult = jsonObject.get("last_result")
        botState.uid = jsonObject.get("uid")
        botState.previousUid = jsonObject.get("previous_uid")
        botState._sessionData = jsonObject.get("session_data")
        botState._sessionDataType = jsonObject.get("session_data_type")
        botState._sessionUtterances = jsonObject.get("session_utterances")
        botState._sessionUtterancesType = jsonObject.get("session_utterances_type")
        botState._sessionUtterancesOrdered = jsonObject.get(
            "session_utterances_ordered")
        botState._sessionUtterancesPrompt = jsonObject.get(
            "session_utterances_prompt")
        if botState._sessionUtterancesPrompt is None:
            log.debug("botState._sessionUtterancesPrompt = {}")
            botState._sessionUtterancesPrompt = {}
        botState._sessionApiResults = {}
        _d = jsonObject.get("session_api_results", {})
        for (k,v) in _d.iteritems():
            botState._sessionApiResults[k] = InferenceResult.fromJSON(v)
            
        botState.writeTime = jsonObject.get("write_time")
        botState.sessionIntent = jsonObject.get("session_intent")
        botState.sessionId = jsonObject.get("session_id")
        botState.sessionStartTime = jsonObject.get("session_start_time")
        return botState

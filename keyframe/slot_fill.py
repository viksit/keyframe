from __future__ import absolute_import
import sys
import logging
import inspect
from . import messages
from . import misc
from six import add_metaclass
import re
from .dsl import BaseEntity
import json
import six

log = logging.getLogger(__name__)


#@add_metaclass(misc.SlotMeta)
class Slot(object):

    SLOT_STATE_NEW = "new"
    SLOT_STATE_WAITING_FILL = "waiting_for_fill"
    SLOT_STATE_FILLED = "filled"

    SLOT_TYPE_INPUT = "slot-type-input"
    SLOT_TYPE_INFO = "slot-type-info"
    SLOT_TYPE_HIDDEN = "slot-type-hidden"
    SLOT_TYPE_ACTION = "slot-type-action"
    SLOT_TYPE_TRANSFER = "slot-type-transfer"
    SLOT_TYPE_INTENT_MODEL = "slot-type-intent-model"

    # TODO(viksit): overwrite the instance variables from the class variable

    def __init__(self, apiResult=None, newTopic=None, topicId=None, config=None,
                 tags=None):
        # If there are multiple slots with the same class, the slot definition
        # will have to override this and give some names.
        self.name = re.sub(r"(.)([A-Z])", r"\1_\2", self.__class__.__name__).lower()
        self.tags = tags
        self.config = config
        self.entityName = self.name
        self.filled = False
        self.value = None
        self.validated = False
        self.state = Slot.SLOT_STATE_NEW
        self.required = False
        self.parseOriginal = False
        self.useSlotsForParse = []
        self.parseResponse = False
        self.optionsList = None
        self.entityType = None
        self.apiResult = apiResult
        self.newTopic = newTopic
        self.topicId = topicId
        self.canonicalMsg = None
        self.displayType = None
        self.slotType = None
        self.descName = None
        self.useStored = False

    def __repr__(self):
        return "%s" % (json.dumps(self.toJSONObject()),)

    def toJSONObject(self):
        return {
            "className": self.__class__.__name__,
            "name": self.name,
            "descName": self.descName,
            "filled": self.filled,
            "value": self.value,
            "validated": self.validated,
            "state": self.state,
            "parseOriginal": self.parseOriginal,
            "parseResponse": self.parseResponse,
            "entity": self.entity.toJSON(),
            "required": self.required,
            "optionsList":self.optionsList,
            "entityName":self.entityName,
            "slotType":self.slotType,
            "useSlotsForParse":self.useSlotsForParse
        }

    def fromJSONObject(self, j):
        self.name = j.get("name")
        self.descName = j.get("descName")
        self.entityName = j.get("entityName")
        self.filled = j.get("filled")
        self.value = j.get("value")
        self.validated = j.get("validated")
        self.state = j.get("state")
        self.parseOriginal = j.get("parseOriginal")
        self.parseResponse = j.get("parseResponse")
        self.entity = BaseEntity.fromJSON(j.get("entity"))
        self.required = j.get("required")
        self.optionsList = j.get("optionsList"),
        self.slotType = j.get("slotType")
        self.useSlotsForParse = j.get("useSlotsForParse", [])

    def init(self, **kwargs):
        self.channelClient = kwargs.get("channelClient")
        self.state = "new" # or process_slot

    def addCustomFieldsToSession(self, botState):
        if self.customFields:
            for (k,v) in six.iteritems(self.customFields):
                botState.addToSessionData(k, v, self.entityType)

    def fillWrapper(self, canonicalMsg, apiResult, channelClient, botState):
        log.info("fillWrapper called with apiResult: %s", apiResult)
        self.addCustomFieldsToSession(botState)
        return self.fill(canonicalMsg, apiResult, channelClient, botState)

    def fill(self, canonicalMsg, apiResult, channelClient, botState):
        """
        if parseOriginal is true
          analyze the intent canonicalMsg to see if we can extract
          if extracted
            fill the slot
          else
            continue
        ask a question of the user, get response
        if parseResponse is True
          extract the entity from the response
        else
          take the whole response and fill the slot with it
        """
        log.info("fill called with text: %s", canonicalMsg.text)
        self.apiResult = apiResult
        self.channelClient = channelClient
        self.canonicalMsg = canonicalMsg

        # TODO(viksit): Make this cleaner
        # We may want to interpret the response via an entity matcher
        # but this may be a regex entity or a non api entity as well.
        # This is not required.
        # if self.parseOriginal is True:
        #     assert self.apiResult is not None
        # if self.parseResponse is True:
        #     assert self.apiResult is not None

        fillResult = None
        canonicalResponse = None
        if self.state == Slot.SLOT_STATE_NEW:
            log.debug("(1) state: %s", self.state)
            log.debug("parseoriginal: %s", self.parseOriginal)
            # Check if this slots id is already in entities.
            existingEntity = botState.getSessionData().get(self.entityName)
            if existingEntity and self.useStored:
                log.info("This entityName (%s) is already present in botState.sessionData (%s) - I can just move on.", self.entityName, existingEntity)
                self.value = existingEntity
                self.filled = True
                return {"status":self.filled}

            if self.parseOriginal is True:
                parseTextList = []
                for parseSlotName in self.useSlotsForParse:
                    log.debug("looking for slot to parse: %s", parseSlotName)
                    pText = botState.getSessionData().get(parseSlotName)
                    pApiResult = botState.getSessionApiResults().get(parseSlotName)
                    if pText:
                        log.debug("adding slot to parse: %s, %s, %s", parseSlotName, pText, type(pApiResult))
                        parseTextList.append((pText, pApiResult))
                fillResult = None
                if canonicalMsg.text:
                    parseTextList.insert(0, (canonicalMsg.text, self.apiResult))
                fillText = None
                fillApiResult = None
                for (parseText, parseApiResult) in parseTextList:
                    fillResult = self._extractSlotFromSentence(
                        parseText, parseApiResult)
                    log.debug("fillresult: %s", fillResult)
                    if fillResult:
                        fillText = parseText
                        fillApiResult = parseApiResult
                        break
                if fillResult:
                    self.value = fillResult
                    botState.addToSessionData(
                        self.name, self.value, self.entityType)
                    botState.addToSessionUtterances(
                        self.name,
                        canonicalMsg.text, self.prompt(botState), self.entityType)
                    botState.addToSessionApiResults(
                        self.name, fillApiResult)
                    self.filled = True
                    return {"status":self.filled}

            # The original sentence didn't have any items to fill this slot
            # Send a response
            canonicalResponse = self._createAndSendResponse(
                self.prompt(botState), channelClient,
                responseType=messages.ResponseElement.RESPONSE_TYPE_SLOTFILL,
                botStateUid=botState.getUid())
            self.state = Slot.SLOT_STATE_WAITING_FILL

        # Waiting for user response
        elif self.state == Slot.SLOT_STATE_WAITING_FILL:
            log.debug("(2) state: %s", self.state)
            # If we want the incoming response to be put through an entity extractor
            if self.parseResponse is True:
                log.debug("parse response is true")
                fillResult = self._extractSlotFromSentence(
                    canonicalMsg.text, self.apiResult)
                if fillResult:
                    self.value = fillResult
                    botState.addToSessionData(
                        self.name, self.value, self.entityType)
                    botState.addToSessionUtterances(
                        self.name,
                        canonicalMsg.text, self.prompt(botState), self.entityType)
                    botState.addToSessionApiResults(
                        self.name,
                        self.apiResult)
                    self.filled = True
                    self.state = Slot.SLOT_STATE_FILLED
                else:
                    # We notify the user that this value is invalid.
                    # ask to re-fill.
                    # currently this is an inifnite loop.
                    # TODO(viksit/nishant): add a nice way to control this.
                    log.warn("Incorrect value (%s) entered for slot %s.", fillResult, self.name)
                    msg = "You entered an incorrect value. Please enter again."
                    canonicalResponse = self._createAndSendResponse(
                        msg, channelClient,
                        responseType=messages.ResponseElement.RESPONSE_TYPE_SLOTFILL_RETRY,
                        botStateUid=botState.getUid())
                    self.state = Slot.SLOT_STATE_WAITING_FILL
                    self.filled = False
                    return {"status":self.filled, "response":canonicalResponse}
            # Otherwise we just take the whole utterance and incorporate it.
            else:
                fillResult = self.canonicalMsg.text
                self.value = fillResult
                botState.addToSessionData(self.name, self.value, self.entityType)
                botState.addToSessionUtterances(
                    self.name,
                    canonicalMsg.text, self.prompt(botState), self.entityType)
                botState.addToSessionApiResults(
                    self.name,
                    self.apiResult)
                self.filled = True
                self.state = Slot.SLOT_STATE_FILLED
        elif self.state == Slot.SLOT_STATE_FILLED:
            log.warn("This slot is already filled with value: %s", self.value)
            raise Exception(
                ("Came across a slot that is already filled!"
                " This probably means an endless loop."))

        if canonicalResponse:
            return {"status":self.filled, "response":canonicalResponse}
        else:
            return {"status":self.filled}


    def _createAndSendResponse(
            self, msg, channelClient,
            responseType=messages.ResponseElement.RESPONSE_TYPE_RESPONSE,
            botStateUid=None):
        #log.info("_createAndSendResponse(%s)", locals())
        cr = None
        if self.entityType in ("OPTIONS", "ENUM"):
            cr = messages.createOptionsResponse(
                self.canonicalMsg,
                msg,
                self.optionsList,
                responseType,
                responseMeta=messages.ResponseMeta(
                    apiResult=self.apiResult,
                    newTopic=self.newTopic,
                    topicId=self.topicId),
                displayType=self.displayType,
                botStateUid=botStateUid)
        elif self.entityType == "ATTACHMENTS":
            cr = messages.createAttachmentsResponse(
                self.canonicalMsg,
                msg,
                responseType,
                responseMeta=messages.ResponseMeta(
                    apiResult=self.apiResult,
                    newTopic=self.newTopic,
                    topicId=self.topicId),
                botStateUid=botStateUid)
        else:
            cr = messages.createTextResponse(
                self.canonicalMsg,
                msg,
                responseType,
                responseMeta=messages.ResponseMeta(
                    apiResult=self.apiResult,
                    newTopic=self.newTopic,
                    topicId=self.topicId),
                botStateUid=botStateUid,
                inputExpected=True)
        channelClient.sendResponse(cr)
        return cr

    def _extractSlotFromSentence(self, text, apiResult):
        """
        Take a given sentence.
        For the current slot, run the entity_extract_fn() on it

        The return value of this is what we give to the result
        """
        res = None
        log.info("_extractSlotFromSentence: %s with entity: %s from %s with apiResult %s", self.name, self.entity, text, type(apiResult))
        res = self.entity.entity_extract_fn(
            text=text, apiResult=apiResult)
        if res:
            log.info("(a) Slot was filled in this sentence")
        # Return final result
        log.info("_extractSlotFromSentence returning %s", res)
        return res

    def getActionType(self):
        return None

    def get(self):
        pass

    def prompt(self, botState):
        raise NotImplementedError()

    def validate(self):
        pass

    def reset(self):
        # Only change the modifiable stuff
        self.value = None
        self.validated = False
        self.filled = False

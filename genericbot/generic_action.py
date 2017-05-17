from __future__ import print_function
import logging
import urlparse
import copy
import uuid
from collections import defaultdict
import sys
from jinja2 import Template
import requests
import json
from six import iteritems, add_metaclass
import traceback
import keyframe.email

import keyframe.constants as constants
import keyframe.actions
import keyframe.dsl as dsl
import keyframe.slot_fill as slot_fill
import generic_slot
import keyframe.messages as messages
import keyframe.utils
import integrations.zendesk.zendesk as zendesk
import keyframe.event_writer as event_writer
import keyframe.event

log = logging.getLogger(__name__)
#log.setLevel(20)

class GenericActionObject(keyframe.actions.ActionObject):

    def __init__(self, **kwargs):
        super(GenericActionObject, self).__init__(**kwargs)
        self.msg = None
        self.specJson = None
        self.slotsType = None
        self.nextSlotToFill = None

    def getPreemptWaitingActionThreshold(self):
        if self.specJson:
            return self.specJson.get("preempt_waiting_action_threshold")
        return None

    def getClearWaitingAction(self):
        if self.specJson:
            return self.specJson.get("clear_waiting_action", False)
        return False

    def getSlots(self):
        raise Exception("This should not be used")


    # TODO(viksit): make this more centralized.
    ENTITY_TYPE_CLASS_MAP = {
        "PERSON": dsl.PersonEntity,
        "FREETEXT": dsl.FreeTextEntity,
        "LOCATION": dsl.LocationEntity,
        "DATE": dsl.DateEntity,
        "ORGANIZATION": dsl.OrgEntity,
        "PHONE": dsl.PhoneRegexEntity,
        "EMAIL": dsl.EmailRegexEntity,
        "OPTIONS": dsl.OptionsEntity,
        "ATTACHMENTS":dsl.AttachmentsEntity
    }
    def getEntityClassFromType(self, entityType):
        if entityType in self.ENTITY_TYPE_CLASS_MAP:
            return self.ENTITY_TYPE_CLASS_MAP[entityType]
        return self.ENTITY_TYPE_CLASS_MAP.get("FREETEXT")

    def slotFill(self, botState):
        """Return True if all slots are filled, false otherwise.
        """
        if self.slotsType == self.SLOTS_TYPE_CONDITIONAL:
            return self.slotFillConditional(botState)
        else:
            return super(GenericActionObject, self).slotFill(botState)

    def slotFillConditional(self, botState):
        """
        Function to do slot fill per action object.
        Returns:
          True if all required slots are filled.
          False if all required slots haven't been filled yet or something went wrong.
        """
        log.info("slotFillConditional called")
        while True:
            log.info("self.nextSlotToFillName: %s", self.nextSlotToFillName)
            assert self.nextSlotToFillName, "No nextSlotToFillName!"
            slotObject = self.slotObjectsByName[self.nextSlotToFillName]
            assert slotObject
            if slotObject.slotType == slot_fill.Slot.SLOT_TYPE_TRANSFER:
                # Decision was to not have a prompt for transfer slots.
                #slotObject.sendMessageIfAny(
                #    self.canonicalMsg, self.apiResult, self.channelClient,
                #    botState)
                transferTopicId = slotObject.getTransferTopicId()
                assert transferTopicId, "Trying to transfer without transferTopicId"
                botState.setTransferTopicId(transferTopicId)
                return constants.BOT_REQUEST_STATE_TRANSFER
            filled = slotObject.fill(
                self.canonicalMsg, self.apiResult, self.channelClient,
                botState)

            responseEvent = keyframe.event.createEvent(
                eventType="response", src="agent",
                sessionStatus=None, # to be filled below
                sessionId=botState.getSessionId(),
                userId=self.canonicalMsg.userId,
                topicId=self.originalTopicId,
                topicType=self.getTopicType(),
                slotId=slotObject.name,
                slotType=slotObject.slotType,
                actionType=slotObject.getActionType(),
                responseType=None,  # to be filled below
                ticketFiled=False,  # updated if required below
                resolutionStatus=False
            )
            eventWriter = event_writer.getWriter()
            if filled:
                responseEvent.responseType = "fill"
                if slotObject.getActionType() == "zendesk":
                    responseEvent.ticketFiled = True
            if not filled:
                responseEvent.responseType = "prompt"
                botState.putWaiting(self.toJSONObject())
                log.debug("slotFillConditional: returning False - not filled")
                eventWriter.write(responseEvent.toJSONStr(), responseEvent.userId)
                return constants.BOT_REQUEST_STATE_PROCESSED
            if not slotObject.slotTransitions:
                log.debug("slotFillConditional: returning True")
                if self.getTopicType() == "resolution":
                    responseEvent.sessionStatus = "end"
                    responseEvent.resolutionStatus = True
                eventWriter.write(responseEvent.toJSONStr(), responseEvent.userId)
                return constants.BOT_REQUEST_STATE_PROCESSED
            self.nextSlotToFillName = slotObject.slotTransitions.get(
                slotObject.value)
            log.info("self.nextSlotToFillName: %s", self.nextSlotToFillName)
            if not self.nextSlotToFillName:
                self.nextSlotToFillName = slotObject.slotTransitions.get("__default__")
            if not self.nextSlotToFillName:
                assert slotObject.slotType != slot_fill.Slot.SLOT_TYPE_INTENT_MODEL, "Intent slots should always have an edge to another slot"
                log.info("slotFillConditional: returning True")
                if self.getTopicType() == "resolution":
                    responseEvent.sessionStatus = "end"
                    responseEvent.resolutionStatus = True
            eventWriter.write(responseEvent.toJSONStr(), responseEvent.userId)
            if not self.nextSlotToFillName:
                return constants.BOT_REQUEST_STATE_PROCESSED

    def toJSONObject(self):
        jsonObject = super(GenericActionObject, self).toJSONObject()
        jsonObject["nextSlotToFillName"] = self.nextSlotToFillName
        return jsonObject

    def fromJSONObject(self, actionObjectJSON):
        super(GenericActionObject, self).fromJSONObject(actionObjectJSON)
        self.nextSlotToFill = actionObjectJSON.get(
            "nextSlotToFillName", self.nextSlotToFill)

    @classmethod
    def createActionObject(cls, specJson, topicId, canonicalMsg, botState,
                           userProfile, requestState, api, channelClient,
                           actionObjectParams={},
                           apiResult=None, newTopic=None):
        log.debug("GenericActionObject.createActionObject(%s)", locals())

        # Create a GenericActionObject using specJson
        actionObject = cls()
        actionObject.specJson = specJson
        actionObject.slotsType = specJson.get(
            "slots_type", cls.SLOTS_TYPE_CONDITIONAL)
        slots = specJson.get("slots", [])

        slotObjects = []
        slotObjectsByName = {}
        runAPICall = False
        for slotSpec in slots:
            slotType = slotSpec.get("slot_type")
            assert slotType, "all slots must have an explicit slot type specified"
            log.debug("creating slot: %s slotType: %s",
                      slotSpec.get("name"), slotType)
            gc = None
            if slotType == slot_fill.Slot.SLOT_TYPE_INFO:
                gc = generic_slot.GenericInfoSlot(
                    apiResult=apiResult, newTopic=newTopic,
                    topicId=topicId, channelClient=channelClient)
            elif slotType == slot_fill.Slot.SLOT_TYPE_INTENT_MODEL:
                gc = generic_slot.GenericIntentModelSlot(
                    apiResult=apiResult, newTopic=newTopic,
                    topicId=topicId, channelClient=channelClient, api=api)
                gc.intentModelId = slotSpec.get("intent_model_id")
                gc.outlierCutoff = slotSpec.get("outlier_cutoff")
                gc.outlierFrac = slotSpec.get("outlier_frac")
            elif slotType == slot_fill.Slot.SLOT_TYPE_HIDDEN:
                gc = generic_slot.GenericHiddenSlot(
                    apiResult=apiResult, newTopic=newTopic,
                    topicId=topicId)
                gc.customFields = slotSpec.get("custom_fields")
                assert gc.customFields, "Hidden slot must have customFields"
            elif slotType == slot_fill.Slot.SLOT_TYPE_ACTION:
                gc = generic_slot.GenericActionSlot(
                    apiResult=apiResult, newTopic=newTopic,
                    topicId=topicId, channelClient=channelClient)
                gc.actionSpec = slotSpec.get("action_spec")
                assert gc.actionSpec, "Action slot must have actionSpec"
            elif slotType == slot_fill.Slot.SLOT_TYPE_INPUT:
                gc = generic_slot.GenericSlot(
                    apiResult=apiResult, newTopic=newTopic, topicId=topicId)
            elif slotType == slot_fill.Slot.SLOT_TYPE_TRANSFER:
                gc = generic_slot.GenericTransferSlot(
                    apiResult=apiResult, newTopic=newTopic, topicId=topicId)
                gc.transferTopicId = slotSpec.get("transfer_topic_id")
                assert gc.transferTopicId, "Transfer slots must have transfer_topic_id defined"
            else:
                raise Exception("Unknown slot type (%s)" % (slotType,))

            gc.slotType = slotType
            gc.promptMsg = slotSpec.get("prompt")
            #assert gc.promptMsg, "slot %s must have a prompt" % (slotSpec,)

            gc.name = slotSpec.get("name")
            gc.descName = slotSpec.get("desc_name")
            assert gc.name, "slot %s must have a name" % (slotSpec,)
            gc.entityName = slotSpec.get("entityName", gc.name)

            required = slotSpec.get("required")
            if not required:
                required = getattr(gc, "required")
                log.debug("slotSpec does not specify required - getting default: %s", required)
            gc.required = required

            parseOriginal = slotSpec.get("parse_original")
            if not parseOriginal:
                parseOriginal = getattr(gc, "parseOriginal")
                log.debug("slotSpec does not specify parseOriginal - getting default :%s", parseOriginal)
            gc.parseOriginal = parseOriginal

            parseResponse = slotSpec.get("parse_response")
            if not parseResponse:
                parseResponse = getattr(gc, "parseResponse")
                log.debug("slotSpec does not specify parseResponse - getting default: %s", parseResponse)
            gc.parseResponse = parseResponse
            log.debug("for slot %s, parseResponse: %s", gc.name, gc.parseResponse)

            gc.displayType = slotSpec.get("slot_input_display_type",
                                          messages.ResponseElement.DISPLAY_TYPE_TEXT)
            log.debug("set slot %s displayType: %s", gc.name, gc.displayType)

            entityType = slotSpec.get("entity_type")
            gc.entityType = entityType
            # If the entity type is not FREETEXT, this should be true
            # override
            if entityType not in ("FREETEXT", "ATTACHMENTS"):
                gc.parseResponse = True
            gc.entity = actionObject.getEntityClassFromType(entityType)(label=gc.name)
            if entityType == "OPTIONS":
                optionsList = slotSpec.get("options_list")
                if not optionsList:
                    raise Exception("must have options_list for slot %s in action object for topic %s" % (gc.name, topicId))
                # From the current UI, the list is specified as a string, but from a newer UI it is a list.
                if isinstance(optionsList, basestring):
                    gc.optionsList = [e.strip() for e in optionsList.strip().split(",") if e.strip()]
                elif isinstance(optionsList, list):
                    gc.optionsList = optionsList
                gc.entity.optionsList = gc.optionsList
                log.debug("set optionsList to %s", gc.optionsList)

            if actionObject.slotsType == cls.SLOTS_TYPE_CONDITIONAL:
                # If a slot does not have slot_transitions, this is the last
                # slot in this path - after it is filled the actionobject is done.
                gc.slotTransitions = slotSpec.get("slot_transitions")
                log.debug("got slot transitions for slot (%s): %s",
                          gc.name, gc.slotTransitions)
            log.debug("created slot: %s", gc)
            slotObjects.append(gc)
            slotObjectsByName[gc.name] = gc
            if gc.entity.needsAPICall:
                runAPICall = True

        # Maintain indent
        actionObject.slotObjects = slotObjects
        actionObject.slotObjectsByName = slotObjectsByName
        if slotObjects:
            if actionObject.slotsType == cls.SLOTS_TYPE_CONDITIONAL:
                # All keys must exist in dict
                actionObject.nextSlotToFillName = slotObjectsByName[
                    specJson["slots_start"]].name
            else:
                raise Exception("bad actionObject.slotsType: %s" % (
                    actionObject.slotsType,))
            log.debug("actionObject.nextSlotToFillName: %s",
                      actionObject.nextSlotToFillName)
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
        if runAPICall:
            assert api, "must have an api to runAPICall"
            apiResult = api.get(canonicalMsg.text)
            actionObject.apiResult = apiResult

        actionObject.canonicalMsg = canonicalMsg
        actionObject.channelClient = channelClient
        actionObject.requestState = requestState
        actionObject.originalTopicId = topicId
        log.debug("createActionObject: %s", actionObject)
        # Action object now contains all the information needed to resolve this action
        return actionObject

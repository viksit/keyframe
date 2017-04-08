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

import keyframe.actions
import keyframe.dsl as dsl
import keyframe.slot_fill as slot_fill
import generic_slot
import keyframe.messages as messages
import keyframe.utils
import integrations.zendesk.zendesk as zendesk

log = logging.getLogger(__name__)
log.setLevel(10)

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

    def getAttachmentUrls(self, filledSlots, slotObjects):
        attachmentUrls = []
        for so in slotObjects:
            if so.entityType == "ATTACHMENTS":
                fUrl = filledSlots.get(so.name)
                if fUrl:
                    if not fUrl.startswith("http"):
                        log.warn("file to upload is not a valid url (%s)", fUrl)
                        continue
                    attachmentUrls.append(fUrl)
        return attachmentUrls

    def fetchWebhook(self, webhook, filledSlots, slotObjects):
        # To render a templatized url with custom parameters
        url = webhook.get("api_url")
        custom = webhook.get("api_params", "{}")
        custom = json.loads(custom) # convert to dict
        entities = filledSlots
        requestBody = webhook.get("api_body")
        requestAuth = webhook.get("api_auth")  # Assume basic auth for now.

        # Response
        urlTemplate = Template(url)
        templatedURL = urlTemplate.render({"custom": custom, "entities": entities})
        log.debug("URL to fetch: %s" % (templatedURL,))
        requestBodyJsonObject = None
        if requestBody:
            log.info("requestBody: %s", requestBody)
            templatedRequestBody = Template(requestBody).render(
                {"custom": custom, "entities": entities})
            log.info("templatedRequestBody (%s): %s", type(templatedRequestBody), templatedRequestBody)
            requestBodyJsonObject = json.loads(templatedRequestBody)

        # Need a zendesk integration. Can't do this generically.
        
        urlPieces = urlparse.urlparse(templatedURL)
        log.debug("urlPieces: %s" % (urlPieces,))
        response = {}
        if not (len(urlPieces.scheme) > 0 and len(urlPieces.netloc) > 0):
            raise Exception("bad api url: %s", templatedUrl)

        requestAuthTuple = None
        if requestAuth:
            requestAuthTuple = tuple(requestAuth.split(":"))
            assert len(requestAuthTuple) == 2, "requestAuth must be a string with format username:password. (%s)" % (requestAuth,)

        if requestBodyJsonObject:
            log.info("making POST request: url: %s, json: %s, auth: %s",
                      templatedURL, requestBodyJsonObject, requestAuthTuple)
            response = requests.post(
                templatedURL, json=requestBodyJsonObject, auth=requestAuthTuple)
        else:
            response = requests.get(templatedURL, auth=requestAuthTuple)
        if response.status_code not in (200, 201, 202):
            log.exception("webhook call failed. status_code: %s", response.status_code)
            raise Exception("webhook call failed. status_code: %s" % (response.status_code,))
        log.info("response (%s): %s" % (type(response), response))
        responseJsonObj = {}
        try:
            responseJsonObj = response.json()
        except ValueError as ve:
            log.warn("could not get json from response to webhook")

        # We've called the webhook with params, now take response
        # And make it available to the text response

        r = webhook.get("response_text", {})
        textResponseTemplate = Template(r)
        renderedResponse = textResponseTemplate.render({
            "entities": filledSlots,
            "response": responseJsonObj
        })
        return renderedResponse

    def doStructuredResponse(self, structuredMsg):
        rt = structuredMsg["response_type"]
        if rt != "email":
            log.warn("unknown response_type: %s", rt)
            return None
        toAddr = Template(structuredMsg.get("to")).render(self.filledSlots)
        subject = Template(structuredMsg.get("subject")).render(self.filledSlots)
        emailContent = Template(structuredMsg.get("body")).render(self.filledSlots)
        r = keyframe.email.send(toAddr, subject, emailContent)
        responseContent = "<no response specified>"
        if r:
            responseContent = structuredMsg.get(
                "success_response",
                structuredMsg.get("response", responseContent))
        else:
            responseContent = structuredMsg.get(
                "failure_response",
                structuredMsg.get("response", responseContent))
        return Template(responseContent).render(self.filledSlots)

    def processZendesk(self, botState):
        zc = copy.deepcopy(self.zendeskConfig.get("request"))
        for (k,v) in self.zendeskConfig.get("request").iteritems():
            log.debug("k: %s, v: %s", k, v)
            zc[k] = Template(v).render(
                {"entities":self.filledSlots})
        if zc.get("attachments").lower() == "all":
            attachmentUrls = self.getAttachmentUrls(
                self.filledSlots, self.slotObjects)
            zc["attachments"] = attachmentUrls
        zr = zendesk.createTicket(zc)
        log.debug("zr (%s): %s", type(zr), zr)
        respTemplate = "A ticket has been filed: {{ticket.url}}"
        respTemplate = self.zendeskConfig.get("response_text", respTemplate)
        log.debug("respTemplate: %s", respTemplate)
        _t = Template(respTemplate)
        resp = _t.render(zr)
        log.debug("after processing zendesk, resp: %s", resp)
        return resp

    def process(self, botState):
        log.debug("GenericAction.process called")
        resp = ""
        structuredMsg = None
        if self.zendeskConfig:
            resp = self.processZendesk(botState)

        if not resp and self.webhook and len(self.webhook.items()):
            resp = self.fetchWebhook(self.webhook, self.filledSlots, self.slotObjects)

        if not resp:
            try:
                log.debug("MSG: %s, (%s)", self.msg, type(self.msg))
                structuredMsg = json.loads(self.msg)
            except ValueError as ve:
                #traceback.print_exc()
                log.info("msg is not json - normal response processing")

            if structuredMsg:
                if "response_type" in structuredMsg:
                    resp = self.doStructuredResponse(structuredMsg)
                else:
                    log.warn("no response_type found in json - skipping structured response")

        log.debug("resp 1: %s", resp)
        if not resp:
            responseTemplate = Template(self.msg)
            log.debug("responseTemplate: %s", responseTemplate)
            _d = {"entities":self.filledSlots}
            log.debug("calling responseTemplate.render with dict: %s", _d)
            resp = responseTemplate.render(_d)
        # Final response
        return self.respond(resp, botStateUid=botState.getUid())

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
            assert self.nextSlotToFillName, "No nextSlotToFillName!"
            slotObject = self.slotObjectsByName[self.nextSlotToFillName]
            assert slotObject
            filled = slotObject.fill(
                self.canonicalMsg, self.apiResult, self.channelClient,
                botState)
            if not filled:
                botState.putWaiting(self.toJSONObject())
                log.debug("slotFillConditional: returning False - not filled")
                return False
            if not slotObject.slotTransitions:
                log.debug("slotFillConditional: returning True")
                return True
            self.nextSlotToFillName = slotObject.slotTransitions.get(
                slotObject.value)
            log.debug("self.nextSlotToFillName: %s", self.nextSlotToFillName)
            if not self.nextSlotToFillName:
                self.nextSlotToFillName = slotObject.slotTransitions.get("__default__")
            if not self.nextSlotToFillName:
                log.debug("slotFillConditional: returning True")
                return True

    def toJSONObject(self):
        jsonObject = super(GenericActionObject, self).toJSONObject()
        jsonObject["nextSlotToFillName"] = self.nextSlotToFillName
        return jsonObject

    def fromJSONObject(self, actionObjectJSON):
        super(GenericActionObject, self).fromJSONObject(actionObjectJSON)
        self.nextSlotToFill = actionObjectJSON.get(
            "nextSlotToFillName", self.nextSlotToFill)

    @classmethod
    def createActionObject(cls, specJson, intentStr, canonicalMsg, botState,
                           userProfile, requestState, api, channelClient,
                           actionObjectParams={},
                           apiResult=None, newIntent=None):
        log.debug("GenericActionObject.createActionObject(%s)", locals())

        # Create a GenericActionObject using specJson
        actionObject = cls()
        actionObject.specJson = specJson
        actionObject.msg = specJson.get("text")
        actionObject.transitionMsg = specJson.get("transition_text")
        actionObject.slotsType = specJson.get(
            "slots_type", cls.SLOTS_TYPE_SEQUENTIAL)
        # TODO: This has to be enforced in the UI.
        #assert actionObject.msg, "No text field in json: %s" % (specJson,)
        if not actionObject.msg:
            actionObject.msg = "<No msg provided by agent spec.>"
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
                    apiResult=apiResult, newIntent=newIntent, intentStr=intentStr)
            elif slotType == slot_fill.Slot.SLOT_TYPE_HIDDEN:
                gc = generic_slot.GenericHiddenSlot(
                    apiResult=apiResult, newIntent=newIntent, intentStr=intentStr)
                gc.customFields = slotSpec.get("custom_fields")
                assert gc.customFields, "Hidden slot must have customFields"
            else:
                gc = generic_slot.GenericSlot(
                    apiResult=apiResult, newIntent=newIntent, intentStr=intentStr)

            gc.slotType = slotType
            gc.promptMsg = slotSpec.get("prompt")
            #assert gc.promptMsg, "slot %s must have a prompt" % (slotSpec,)

            gc.name = slotSpec.get("name")
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
                    raise Exception("must have options_list for slot %s in action object for intent %s" % (gc.name, intentStr))
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
            actionObject.nextSlotToFillName = slotObjects[0].name
            log.debug("actionObject.nextSlotToFillName: %s",
                      actionObject.nextSlotToFillName)
        actionObject.apiResult = apiResult
        actionObject.newIntent = newIntent
        actionObject.instanceId = None
        if newIntent:
            actionObject.instanceId = cls.createActionObjectId()
        actionObject.originalUtterance = None
        if actionObject.newIntent:
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
        actionObject.originalIntentStr = intentStr
        actionObject.webhook = specJson.get("webhook")
        actionObject.zendeskConfig = specJson.get("zendesk")
        log.debug("createActionObject: %s", actionObject)
        # Action object now contains all the information needed to resolve this action
        return actionObject

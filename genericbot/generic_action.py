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
import generic_slot

log = logging.getLogger(__name__)

class GenericActionObject(keyframe.actions.ActionObject):

    def __init__(self, **kwargs):
        super(GenericActionObject, self).__init__(**kwargs)
        self.msg = None
        self.specJson = None

    def getPreemptWaitingActionThreshold(self):
        if self.specJson:
            return self.specJson.get("preempt_waiting_action_threshold")
        return None

    def getClearWaitingAction(self):
        if self.specJson:
            return self.specJson.get("clear_waiting_action", False)
        return False

    def fetchWebhook(self, webhook, filledSlots):
        # To render a templatized url with custom parameters
        url = webhook.get("api_url")
        custom = webhook.get("api_params", "{}")
        custom = json.loads(custom) # convert to dict
        entities = filledSlots

        # Response
        urlTemplate = Template(url)
        templatedURL = urlTemplate.render({"custom": custom, "entities": entities})
        log.debug("URL to fetch: %s" % (templatedURL,))
        urlPieces = urlparse.urlparse(templatedURL)
        log.debug("urlPieces: %s" % (urlPieces,))
        response = {}
        if len(urlPieces.scheme) > 0 and len(urlPieces.netloc) > 0:
            response = requests.get(templatedURL)
            log.info("response (%s): %s" % (type(response), response.json()))
        else:
            log.info("something was wrong with the api url")

        # We've called the webhook with params, now take response
        # And make it available to the text response

        r = webhook.get("response_text", {})
        textResponseTemplate = Template(r)
        renderedResponse = textResponseTemplate.render({
            "entities": filledSlots,
            "response": response.json()
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

    def process(self):
        log.debug("GenericAction.process called")
        resp = ""
        structuredMsg = None
        if self.webhook and len(self.webhook.items()):
            resp = self.fetchWebhook(self.webhook, self.filledSlots)
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
            resp = responseTemplate.render(self.filledSlots)
        # Final response
        return self.respond(resp)

    def getSlots(self):
        raise Exception("This should not be used")


    # TODO(viksit): make this more centralized.
    def getEntityClassFromType(self, entityType):
        mapping = {
            "PERSON": dsl.PersonEntity,
            "FREETEXT": dsl.FreeTextEntity,
            "LOCATION": dsl.LocationEntity,
            "DATE": dsl.DateEntity,
            "ORGANIZATION": dsl.OrgEntity,
            "PHONE": dsl.PhoneRegexEntity,
            "EMAIL": dsl.EmailRegexEntity
        }
        if entityType in mapping:
            return mapping.get(entityType)
        return mapping.get("FREETEXT")

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
        # TODO: This has to be enforced in the UI.
        #assert actionObject.msg, "No text field in json: %s" % (specJson,)
        if not actionObject.msg:
            actionObject.msg = "<No msg provided by agent spec.>"
        slots = specJson.get("slots", [])
        slotObjects = []
        runAPICall = False
        for slotSpec in slots:
            gc = generic_slot.GenericSlot(
                apiResult=apiResult, newIntent=newIntent, intentStr=intentStr)
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

            gc.promptMsg = slotSpec.get("prompt")
            assert gc.promptMsg, "slot %s must have a prompt" % (slotSpec,)

            gc.name = slotSpec.get("name")
            assert gc.name, "slot %s must have a name" % (slotSpec,)

            entityType = slotSpec.get("entity_type")
            # If the entity type is not FREETEXT, this should be true
            # override
            if entityType != "FREETEXT":
                gc.parseResponse = True
            gc.entity = actionObject.getEntityClassFromType(entityType)(label=gc.name)
            slotObjects.append(gc)
            if gc.entity.needsAPICall:
                runAPICall = True

        # Maintain indent
        actionObject.slotObjects = slotObjects
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
            apiResult = api.get(canonicalMsg.text)
            actionObject.apiResult = apiResult

        actionObject.canonicalMsg = canonicalMsg
        actionObject.channelClient = channelClient
        actionObject.requestState = requestState
        actionObject.originalIntentStr = intentStr
        actionObject.webhook = specJson.get("webhook")
        log.debug("createActionObject: %s", actionObject)
        # Action object now contains all the information needed to resolve this action
        return actionObject

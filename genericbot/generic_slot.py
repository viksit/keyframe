import json
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
import integrations.zendesk.zendesk as zendesk
import re

import logging

import keyframe.slot_fill
import keyframe.dsl
import keyframe.messages
import keyframe.utils
import keyframe.constants as constants

log = logging.getLogger(__name__)

class GenericSlot(keyframe.slot_fill.Slot):
    def __init__(self, apiResult=None, newTopic=None,
                 promptMsg=None, topicId=None, channelClient=None):
        super(GenericSlot, self).__init__(
            apiResult=apiResult, newTopic=newTopic, topicId=topicId)
        self.promptMsg = promptMsg
        self.channelClient = channelClient

    # TODO(viksit): This should be defined via the JSON spec file.
    #entity = keyframe.dsl.FreeTextEntity(label="genericentity")
    #required = False
    #parseOriginal = False
    #parseResponse = False
    #optionsList = None

    def prompt(self):
        #assert self.promptMsg
        if self.entityType == "OPTIONS":
            return self.promptMsg
        return self.promptMsg

    def respond(self, text, canonicalMsg, responseType=None, botStateUid=None):
        log.debug("GenericSlot.respond(%s)", locals())

        cr = keyframe.messages.createTextResponse(
            canonicalMsg,
            text,
            responseType,
            responseMeta=keyframe.messages.ResponseMeta(
                apiResult=self.apiResult,
                newTopic=self.newTopic),
            botStateUid=botStateUid)

        self.channelClient.sendResponse(cr)
        return constants.BOT_REQUEST_STATE_PROCESSED

class GenericHiddenSlot(keyframe.slot_fill.Slot):
    def __init__(self, apiResult=None, newTopic=None,
                 topicId=None):
        super(GenericHiddenSlot, self).__init__(
            apiResult=apiResult, newTopic=newTopic,
            topicId=topicId)
        self.customFields = None

    def prompt(self):
        raise Exception("Hidden slots do not have prompts")

    def fill(self, canonicalMsg, apiResult, channelClient, botState):
        self.apiResult = apiResult
        self.channelClient = channelClient
        self.canonicalMsg = canonicalMsg
        self.filled = True
        return self.filled

class GenericTransferSlot(GenericSlot):
    def __init__(self, apiResult=None, newTopic=None,
                 promptMsg=None, topicId=None, channelClient=None):
        super(GenericSlot, self).__init__(
            apiResult=apiResult, newTopic=newTopic, topicId=topicId)
        self.transferTopicId = None

    def getTransferTopicId(self):
        return self.transferTopicId

    def sendMessageIfAny(
            self, canonicalMsg, apiResult, channelClient, botState):
        if not self.prompt():
            return
        self.apiResult = apiResult
        self.channelClient = channelClient
        self.canonicalMsg = canonicalMsg
        # We need to send inputExpected = False for this info slot,
        # so don't use self._createAndSendResponse.
        cr = keyframe.messages.createTextResponse(
            self.canonicalMsg,
            self.prompt(),
            keyframe.messages.ResponseElement.RESPONSE_TYPE_RESPONSE,
            responseMeta=keyframe.messages.ResponseMeta(
                apiResult=self.apiResult,
                newTopic=self.newTopic,
                topicId=self.topicId),
            botStateUid=botState.getUid(),
            inputExpected=False)
        channelClient.sendResponse(cr)

    def fill(self, canonicalMsg, apiResult, channelClient, botState):
        raise Exception("Should not be called for GenericTransferSlot")

class GenericIntentModelSlot(GenericSlot):
    def __init__(self, apiResult=None, newTopic=None,
                 promptMsg=None, topicId=None,
                 channelClient=None, api=None):
        super(GenericIntentModelSlot, self).__init__(
            apiResult=apiResult, newTopic=newTopic,
            topicId=topicId, channelClient=channelClient)
        self.intentModelId = None
        self.outlierCutoff = None
        self.outlierFrac = None
        self.api = api

    intent_str_re = re.compile("\[intent=([^\]]+)\]")
    def _extractDirect(self, canonicalMsg):
        x = self.intent_str_re.match(canonicalMsg.text)
        if x:
            return x.groups()[0]
        return None

    def _extractSlotFromSentence(self, canonicalMsg):
        label = self._extractDirect(canonicalMsg)
        if label:
            log.debug("GOT label from direct: %s", label)
            return label
        log.debug("Calling intent model")
        urlParams = {}
        if canonicalMsg.rid:
            urlParams = {"rid":canonicalMsg.rid}
        apiResult = self.api.get(
            canonicalMsg.text,
            intent_model_id=self.intentModelId,
            url_params=urlParams,
            outlier_cutoff=self.outlierCutoff,
            outlier_frac=self.outlierFrac)
        log.debug("GenericIntentModelSlot.fill apiResult: %s", apiResult)
        return apiResult.intent.label

class GenericInfoSlot(GenericSlot):
    def __init__(self, apiResult=None, newTopic=None,
                 promptMsg=None, topicId=None,
                 channelClient=None):
        super(GenericInfoSlot, self).__init__(
            apiResult=apiResult, newTopic=newTopic,
            topicId=topicId, channelClient=channelClient)

    def prompt(self):
        return self.promptMsg

    def fill(self, canonicalMsg, apiResult, channelClient, botState):
        self.apiResult = apiResult
        self.channelClient = channelClient
        self.canonicalMsg = canonicalMsg
        # We need to send inputExpected = False for this info slot,
        # so don't use self._createAndSendResponse.
        responseMsg = Template(self.prompt()).render(
            {"entities":botState.getSessionData(),
             "utterances":botState.getSessionUtterances()})
        cr = keyframe.messages.createTextResponse(
            self.canonicalMsg,
            responseMsg,
            keyframe.messages.ResponseElement.RESPONSE_TYPE_RESPONSE,
            responseMeta=keyframe.messages.ResponseMeta(
                apiResult=self.apiResult,
                newTopic=self.newTopic,
                topicId=self.topicId),
            botStateUid=botState.getUid(),
            inputExpected=False)
        channelClient.sendResponse(cr)
        self.filled = True
        return self.filled

class GenericActionSlot(GenericSlot):
    def __init__(self, apiResult=None, newTopic=None,
                 topicId=None, channelClient=None):
        super(GenericActionSlot, self).__init__(
            apiResult=apiResult, newTopic=newTopic,
            topicId=topicId)
        self.channelClient = channelClient
        self.actionSpec = None

    def getActionType(self):
        if not self.actionSpec:
            return None
        return self.actionSpec.get("action_type")

    def prompt(self):
        raise Exception("Action slots do not have prompts")

    def fill(self, canonicalMsg, apiResult, channelClient, botState):
        log.debug("GenericActionSlot.fill(%s)", locals())
        assert self.actionSpec, "ActionSlot must have actionSpec"
        self.doAction(canonicalMsg, apiResult, channelClient, botState)
        self.filled = True
        return self.filled

    def doAction(self, canonicalMsg, apiResult, channelClient, botState):
        assert self.actionSpec, "ActionSlot must have an action spec"
        actionType = self.actionSpec.get("action_type").lower()
        if actionType == "zendesk":
            resp = self.processZendesk(botState)
        #elif actionType == "email":
        #    resp = self.doStructuredResponse(
        #        self.actionSpec.get("email"), botState)
        elif actionType == "webhook":
            resp = self.fetchWebhook(
                self.actionSpec.get("webhook"), botState)
        else:
            raise Exception("Unknown actionType (%s)" % (actionType,))
        return self.respond(
            resp, canonicalMsg, botStateUid=botState.getUid())

    def fetchWebhook(self, webhook, botState):
        # To render a templatized url with custom parameters
        url = webhook.get("api_url")
        custom = webhook.get("api_params", "{}")
        custom = json.loads(custom) # convert to dict
        entities = botState.getSessionData()
        requestBody = webhook.get("api_body")
        requestAuth = webhook.get("api_auth")  # Assume basic auth for now.
        log.debug("fetchWebhook entities: %s", entities)
        # Response
        urlTemplate = Template(url)
        templatedURL = urlTemplate.render(
            {"custom": custom, "entities": entities,
             "utterances":botState.getSessionUtterances()})
        log.debug("URL to fetch: %s" % (templatedURL,))
        requestBodyJsonObject = None
        if requestBody:
            log.info("requestBody: %s", requestBody)
            templatedRequestBody = Template(requestBody).render(
                {"custom": custom, "entities": entities,
                 "utterances":botState.getSessionUtterances()})
            log.info("templatedRequestBody (%s): %s", type(templatedRequestBody), templatedRequestBody)
            requestBodyJsonObject = json.loads(templatedRequestBody)

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
            "entities": entities,
            "response": responseJsonObj,
            "utterances": botState.getSessionUtterances()})
        return renderedResponse


    def doEmail(self, emailSpec):
        toAddr = Template(emailSpec.get("to")).render(self.filledSlots)
        subject = Template(emailSpec.get("subject")).render(self.filledSlots)
        emailContent = Template(emailSpec.get("body")).render(self.filledSlots)
        r = keyframe.email.send(toAddr, subject, emailContent)
        responseContent = "<no response specified>"
        if r:
            responseContent = emailSpec.get(
                "success_response",
                emailSpec.get("response", responseContent))
        else:
            responseContent = emailSpec.get(
                "failure_response",
                emailSpec.get("response", responseContent))
        return Template(responseContent).render(self.filledSlots)

    def getAttachmentUrls(self, botState):
        urls = []
        sessionData = botState.getSessionData()
        for (k,v) in botState.getSessionDataType().iteritems():
            if v == "ATTACHMENTS":
                url = sessionData.get(k)
                if url.lower() in ("no","none","no attachment"):
                    continue
                assert url, "Attachment does not have a url value (%s)" % (k,)
                urls.append(url)
        return urls

    def processZendesk(self, botState):
        zendeskConfig = self.actionSpec.get("zendesk")
        zc = copy.deepcopy(zendeskConfig.get("request"))
        entities = botState.getSessionData()
        for (k,v) in zendeskConfig.get("request").iteritems():
            log.debug("k: %s, v: %s", k, v)
            zc[k] = Template(v).render(
                {"entities":entities,
                 "utterances":botState.getSessionUtterances()})
        if zc.get("attachments"):
            if zc.get("attachments").lower() in (
                    "none", "no", "no attachments"):
                zc["attachments"] = None
            if zc.get("attachments").lower() == "all":
                attachmentUrls = self.getAttachmentUrls(botState)
                log.debug("attachmentUrls: %s", attachmentUrls)
                zc["attachments"] = attachmentUrls
            else:
                attachmentUrl = Template(zc.get("attachments")).render(
                    {"entities":entities,
                     "utterances":botState.getSessionUtterances()})
                zc["attachments"] = [attachmentUrl]
        zr = zendesk.createTicket(zc)
        log.debug("zr (%s): %s", type(zr), zr)
        respTemplate = "A ticket has been filed: {{ticket.url}}"
        respTemplate = zendeskConfig.get("response_text", respTemplate)
        log.debug("respTemplate: %s", respTemplate)
        _t = Template(respTemplate)
        resp = _t.render(zr)
        log.debug("after processing zendesk, resp: %s", resp)
        return resp

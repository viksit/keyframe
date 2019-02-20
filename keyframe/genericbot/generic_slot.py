from __future__ import absolute_import
import json
import logging
import six.moves.urllib.parse
import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error
import copy
import uuid
from collections import defaultdict
import sys
from jinja2 import Template
import requests
import json
from six import iteritems, add_metaclass
import traceback
import urllib

import re
import random
import lxml.html

import six

import logging

import keyframe.slot_fill
import keyframe.dsl
import keyframe.messages
import keyframe.utils
import keyframe.constants as constants

import keyframe.intercom_client as intercom_client
import keyframe.channel_client as channel_client

import keyframe.integrations.zendesk.zendesk as zendesk
import keyframe.integrations.salesforce.salesforce as salesforce


log = logging.getLogger(__name__)

class GenericSlot(keyframe.slot_fill.Slot):
    def __init__(self, apiResult=None, newTopic=None,
                 promptMsg=None, topicId=None, channelClient=None,
                 config=None, tags=None):
        super(GenericSlot, self).__init__(
            apiResult=apiResult, newTopic=newTopic, topicId=topicId,
            config=config, tags=tags)
        self.promptMsg = promptMsg
        self.channelClient = channelClient
        self.customFields = None

    # TODO(viksit): This should be defined via the JSON spec file.
    #entity = keyframe.dsl.FreeTextEntity(label="genericentity")
    #required = False
    #parseOriginal = False
    #parseResponse = False
    #optionsList = None


    def prompt(self, botState):
        #assert self.promptMsg
        m = self.promptMsg
        if type(self.promptMsg) == list:
            m = self.promptMsg[random.randint(0, len(self.promptMsg) - 1)]
        ed = self._entitiesDict(botState)
        # TODO(nishant): This is a temporary fix for the userMessages break!
        ed['userMessages'] = {}
        log.info("m: %s", m)
        log.info("ed: %s", ed)
        responseMsg = Template(m).render(ed)
        return responseMsg

    def respond(self, contentType,
                text, canonicalMsg, responseType=None, botStateUid=None,
                searchAPIResult=None, zendeskTicketUrl=None):
        log.debug("GenericSlot.respond(%s)", locals())
        responseMeta=keyframe.messages.ResponseMeta(
            apiResult=self.apiResult,
            newTopic=self.newTopic,
            searchAPIResult=searchAPIResult,
            zendeskTicketUrl=zendeskTicketUrl,
            tags=self.tags)
        if contentType == "text":
            cr = keyframe.messages.createTextResponse(
                canonicalMsg,
                text,
                responseType,
                responseMeta=responseMeta,
                botStateUid=botStateUid)
        elif contentType == "search":
            searchResults = searchAPIResult.get("hits")
            log.debug("searchResults: %s", searchResults)
            if not searchResults:
                cr = keyframe.messages.createTextResponse(
                    canonicalMsg,
                    text,
                    responseType,
                    responseMeta=responseMeta,
                    botStateUid=botStateUid)
            else:
                cr = keyframe.messages.createSearchResponse(
                    canonicalMsg=canonicalMsg, searchResults=searchResults,
                    responseType=responseType,
                    responseMeta=responseMeta, botStateUid=botStateUid,
                    text=text)
        else:
            raise Exception("unknown contentType (%s)" % (contentType,))
        self.channelClient.sendResponse(cr)
        #return constants.BOT_REQUEST_STATE_PROCESSED
        return cr

class GenericHiddenSlot(keyframe.slot_fill.Slot):
    def __init__(self, apiResult=None, newTopic=None,
                 topicId=None, config=None, tags=None):
        super(GenericHiddenSlot, self).__init__(
            apiResult=apiResult, newTopic=newTopic,
            topicId=topicId, config=config, tags=tags)
        self.customFields = None

    def prompt(self, botState):
        raise Exception("Hidden slots do not have prompts")

    def fill(self, canonicalMsg, apiResult, channelClient, botState):
        self.apiResult = apiResult
        self.channelClient = channelClient
        self.canonicalMsg = canonicalMsg
        self.filled = True
        return {"status":self.filled}

class GenericTransferSlot(GenericSlot):
    def __init__(self, apiResult=None, newTopic=None,
                 promptMsg=None, topicId=None, channelClient=None,
                 config=None, tags=None):
        super(GenericSlot, self).__init__(
            apiResult=apiResult, newTopic=newTopic, topicId=topicId,
            config=config, tags=tags)
        self.transferTopicId = None
        self.transferTopicNodeId = None

    def getTransferTopicInfo(self):
        startNewSession = False
        if self.customFields:
            startNewSession = self.customFields.get("start_new_session", False)
        return {"transferTopicId":self.transferTopicId,
                "transferTopicNodeId":self.transferTopicNodeId,
                "startNewSession":startNewSession}

    def sendMessageIfAny(
            self, canonicalMsg, apiResult, channelClient, botState):
        if not self.prompt(botState):
            return
        self.apiResult = apiResult
        self.channelClient = channelClient
        self.canonicalMsg = canonicalMsg
        # We need to send inputExpected = False for this info slot,
        # so don't use self._createAndSendResponse.
        cr = keyframe.messages.createTextResponse(
            self.canonicalMsg,
            self.prompt(botState),
            keyframe.messages.ResponseElement.RESPONSE_TYPE_RESPONSE,
            responseMeta=keyframe.messages.ResponseMeta(
                apiResult=self.apiResult,
                newTopic=self.newTopic,
                topicId=self.topicId,
                tags=self.tags),
            botStateUid=botState.getUid(),
            inputExpected=False)
        channelClient.sendResponse(cr)
        return cr

    def fill(self, canonicalMsg, apiResult, channelClient, botState):
        raise Exception("Should not be called for GenericTransferSlot")

class GenericIntentModelSlot(GenericSlot):
    def __init__(self, apiResult=None, newTopic=None,
                 promptMsg=None, topicId=None,
                 channelClient=None, api=None,
                 intentModelParams=None,
                 regexMatcherJson=None,
                 config=None, tags=None):
        super(GenericIntentModelSlot, self).__init__(
            apiResult=apiResult, newTopic=newTopic,
            topicId=topicId, channelClient=channelClient,
            config=config, tags=tags)
        self.intentModelId = None
        self.api = api
        self.intentModelParams = intentModelParams
        self.regexMatcherJson = regexMatcherJson

    intent_str_re = re.compile("\[intent=([^\]]+)\]")
    def _extractDirect(self, text):
        x = self.intent_str_re.match(text)
        if x:
            return x.groups()[0]
        return None

    @classmethod
    def checkRegexMatch(cls, text, regexMatcherJson):
        """regexMatcher is a list [(intent_str:regex_str)]
        """
        for d in regexMatcherJson:
            log.info("d: %s (%s)", d, type(d))
            assert len(d) == 1
            intentStr = list(d.keys())[0]
            regexStrList = list(d.values())[0]
            for regexStr in regexStrList:
                log.debug("comparing text (%s) with regexStr (%s)",
                          text, regexStr)
                tmp = re.search(regexStr, text)
                if tmp:
                    return intentStr
        return None

    def _extractSlotFromSentence(self, text, apiResult):
        label = self._extractDirect(text)
        if label:
            log.debug("GOT label from direct: %s", label)
            return label
        if self.regexMatcherJson:
            intent = self.checkRegexMatch(
                text, self.regexMatcherJson)
            if intent:
                log.info("GOT label from regexMatch: %s", intent)
                return intent
        if not self.intentModelId:
            return "__unknown__"
        if apiResult and apiResult.intent and apiResult.intent.label:
            return apiResult.intent.label

        log.debug("Calling intent model")
        urlParams = {}
        # We now can't pass the whole canonicalMsg because we need to look at past slots.
        # if canonicalMsg.rid:
        #     urlParams = {"rid":canonicalMsg.rid}
        # We're not going to pass model params from keyframe - they will
        # be looked up by the inference_proxy.
        if False:
            modelInvocationParams = {}
            if self.intentModelParams:
                _d = self.intentModelParams.get(
                    "model_invocation_params", {})
                modelInvocationParams = _d.get("default", {})
                modelInvocationParams.update(
                    _d.get(self.intentModelId, {}))
            log.info("modelInvocationParams: %s", modelInvocationParams)
            #urlParams.update(modelInvocationParams)
        apiResult = self.api.get(
            text,
            intent_model_id=self.intentModelId,
            url_params=urlParams)
        log.debug("GenericIntentModelSlot.fill apiResult: %s", apiResult)
        return apiResult.intent.label

class GenericInfoSlot(GenericSlot):
    def __init__(self, apiResult=None, newTopic=None,
                 promptMsg=None, topicId=None,
                 channelClient=None,
                 config=None, tags=None):
        super(GenericInfoSlot, self).__init__(
            apiResult=apiResult, newTopic=newTopic,
            topicId=topicId, channelClient=channelClient,
            config=config, tags=tags)

    def fill(self, canonicalMsg, apiResult, channelClient, botState):
        log.info("GenericInfoSlot.fill called with txt: %s", canonicalMsg.text)
        self.apiResult = apiResult
        self.channelClient = channelClient
        self.canonicalMsg = canonicalMsg
        # We need to send inputExpected = False for this info slot,
        # so don't use self._createAndSendResponse.
        responseMsg = self.prompt(botState)
        cr = None
        if responseMsg:
            cr = keyframe.messages.createTextResponse(
                self.canonicalMsg,
                responseMsg,
                keyframe.messages.ResponseElement.RESPONSE_TYPE_RESPONSE,
                responseMeta=keyframe.messages.ResponseMeta(
                    apiResult=self.apiResult,
                    newTopic=self.newTopic,
                    topicId=self.topicId,
                    tags=self.tags),
                botStateUid=botState.getUid(),
                inputExpected=False)
            channelClient.sendResponse(cr)
            botState.addToSessionUtterances(
                self.name, None, responseMsg, self.entityType)
            if self.canonicalId:
                botState.addToSessionUtterances(
                    self.canonicalId, None, responseMsg, self.entityType,
                    addToTranscript=False)

        self.filled = True
        return {"status":self.filled, "response":cr}

class GenericActionSlot(GenericSlot):
    def __init__(self, apiResult=None, newTopic=None,
                 topicId=None, channelClient=None, config=None,
                 searchIndex=None, agentId=None, tags=None,
                 contactChannelsConfig=None):
        log.info("GenericActionSlot.__init__(config=%s, searchIndex=%s, agentId=%s)",
                 config, searchIndex, agentId)
        super(GenericActionSlot, self).__init__(
            apiResult=apiResult, newTopic=newTopic,
            topicId=topicId, config=config, tags=tags)
        self.channelClient = channelClient
        self.searchIndex = searchIndex
        self.agentId = agentId
        self.actionSpec = None
        self.contactChannelsConfig = contactChannelsConfig

    def getActionType(self):
        if not self.actionSpec:
            return None
        return self.actionSpec.get("action_type")

    def prompt(self, botState):
        raise Exception("Action slots do not have prompts")

    def fill(self, canonicalMsg, apiResult, channelClient, botState):
        log.debug("GenericActionSlot.fill(%s)", locals())
        assert self.actionSpec, "ActionSlot must have actionSpec"
        canonicalResponse = self.doAction(
            canonicalMsg, apiResult, channelClient, botState)
        self.filled = True
        return {"status":self.filled, "response":canonicalResponse}


    def doAction(self, canonicalMsg, apiResult, channelClient, botState):
        assert self.actionSpec, "ActionSlot must have an action spec"
        actionType = self.actionSpec.get("action_type").lower()
        text = None
        ticket_url = None
        searchAPIResult = None
        contentType = "text"
        if actionType == "zendesk":
            _d = self.processZendesk(botState)
            log.debug("ZENDESK returns: %s", _d)
            text = _d.get("text")
            ticket_url = _d.get("ticket_url")
        elif actionType == "salesforce":
            _d = self.processSalesforce(botState)
            log.debug("SALESFORCE returns: %s", _d)
            text = _d.get("text")
            ticket_url = _d.get("ticket_url")
        elif actionType == "email":
            text = self.doEmail(
                self.actionSpec.get("email"), botState)
        elif actionType == "webhook":
            _d = self.fetchWebhookAndFormat(
                self.actionSpec.get("webhook"), botState)
            text = _d.get("text")
            searchAPIResult = _d.get("api_response")
            botState.addToSessionData(
                self.name, _d.get("text"), self.entityType)
            if self.canonicalId:
                botState.addToSessionData(
                    self.canonicalId, _d.get("text"), self.entityType)
            botState.addToSessionUtterances(
                self.name, None, _d.get("text"), self.entityType)
            if self.canonicalId:
                botState.addToSessionUtterances(
                    self.canonicalId, None,
                    _d.get("text"), self.entityType,
                    addToTranscript=False)

            if _d.get("api_response"):
                log.debug("adding to session webhook results: %s", _d.get("api_response"))
                botState.addToSessionWebhookResults(
                    self.name, _d.get("api_response"))
                if self.canonicalId:
                    botState.addToSessionWebhookResults(
                        self.canonicalId, _d.get("api_response"))

        elif actionType == "search":
            searchWebhook = copy.deepcopy(self.actionSpec.get("webhook"))
            searchUrl = self._addSearchDefaults(searchWebhook.get("api_url"))
            searchWebhook["api_url"] = searchUrl
            _d = self.fetchWebhookAndFormat(
                searchWebhook, botState)
            text = _d.get("text")
            searchAPIResult = _d.get("api_response")
            searchAPIResult["num_results"] = len(searchAPIResult.get("hits", []))
            contentType = "search"
            botState.addToSessionData(
                self.name, _d.get("text"), self.entityType)
            if self.canonicalId:
                botState.addToSessionData(
                    self.canonicalId, _d.get("text"), self.entityType)
            botState.addToSessionUtterances(
                self.name, None, _d.get("text"), self.entityType)
            if self.canonicalId:
                botState.addToSessionUtterances(
                    self.canonicalId, None, _d.get("text"), self.entityType,
                    addToTranscript=False)
            botState.addToSessionSearchApiResults(
                self.name, searchAPIResult)
            if self.canonicalId:
                botState.addToSessionSearchApiResults(
                    self.canonicalId, searchAPIResult)

        elif actionType == "transfer_cnv":
            if isinstance(channelClient, channel_client.ChannelClientIntercom):
                assigneeId = channelClient.supportAdminId
                adminId = channelClient.proxyAdminId
                assert assigneeId and adminId, "Must have assigneeId and adminId"
                log.info("TRANSFER_CONVERSATION: %s", channelClient.conversationId)
                intercomClient = intercom_client.IntercomClient(
                    accessToken=self.channelClient.userAccessToken)
                intercomClient.reassignConversation(
                    conversationId=channelClient.conversationId,
                    assigneeId=assigneeId,
                    adminId=adminId)
                text = ""
            else:
                text = "Simulating Intercom message transfer...... beep beep beep beep....... Done."
        else:
            raise Exception("Unknown actionType (%s)" % (actionType,))

        canonicalResponse = self.respond(
            contentType,
            text, canonicalMsg, botStateUid=botState.getUid(),
            searchAPIResult=searchAPIResult, zendeskTicketUrl=ticket_url)
        return canonicalResponse

    def _addSearchDefaults(self, apiUrl):
        """Return the right apiUrl for search.
        """
        log.info("_addSearchDefaults(%s)", apiUrl)
        x = six.moves.urllib.parse.urlparse(apiUrl)
        if x.scheme and x.netloc and x.path and x.query:
            return apiUrl

        assert not (x.scheme and x.netloc)
        log.info("No search server specified. Assuming only parameters are specified and will add search server and path")
        urlTuple = [self.config.HTTP_SCHEME, self.config.MYRA_SEARCH_SERVER, self.config.MYRA_SEARCH_ENDPOINT, '', '', '']
        # Assume anything specified in the webhook url are url parameters
        params = {}
        if apiUrl:
            params = dict(six.moves.urllib.parse.parse_qsl(apiUrl))
        # Need to add two parameters for search if they are not explicitly specified.
        if "idx" not in params:
            params["idx"] = self.searchIndex
        if "agentid" not in params:
            params["agentid"] = self.agentId
        queryStr = six.moves.urllib.parse.urlencode([(k,v) for (k,v) in six.iteritems(params)])
        queryStr = six.moves.urllib.parse.unquote(queryStr)  # for the {{xxx}} placeholders
        urlTuple[4] = queryStr
        newUrl = six.moves.urllib.parse.urlunparse(urlTuple)
        log.info("_addSearchDefaults returning new url: %s", newUrl)
        return newUrl


    def fetchWebhookAndFormat(self, webhook, botState):
        responseJsonObj = self.fetchWebhook(webhook, botState)
        # We've called the webhook with params, now take response
        # And make it available to the text response
        r = webhook.get("response_text", "")
        log.info("RESPONSE TEXT: %s", r)
        textResponseTemplate = Template(r)
        _ed = self._entitiesDict(botState)
        _ed["response"] = responseJsonObj
        renderedResponse = textResponseTemplate.render(_ed)
        return {"text":renderedResponse,
                "api_response":responseJsonObj}

    def fetchWebhook(self, webhook, botState):
        # To render a templatized url with custom parameters
        url = webhook.get("api_url")
        custom = webhook.get("api_params")
        log.info("custom: %s", custom)
        if not custom:
            custom = "{}"
        custom = json.loads(custom) # convert to dict
        entities = botState.getSessionData()
        encodedEntities = copy.deepcopy(entities)
        for k in encodedEntities:
            v = encodedEntities[k]
            log.info("k: %s, v: %s", k, v)
            if v and isinstance(v, str):
                encodedEntities[k] = urllib.parse.quote_plus(v)

        requestBody = webhook.get("api_body")
        requestAuth = webhook.get("api_auth")  # Assume basic auth for now.
        timeoutSeconds = webhook.get("timeout_seconds", 15)
        log.debug("fetchWebhook entities: %s", encodedEntities)
        # Response
        log.info("fetchWebhook URL: %s", url)
        urlTemplate = Template(url)
        templatedURL = urlTemplate.render(
            {"custom": custom, "entities": encodedEntities,
             "utterances":botState.getSessionUtterances()})
        log.debug("URL to fetch: %s" % (templatedURL,))
        requestBodyJsonObject = None
        if requestBody:
            #log.debug("requestBody: %s", requestBody)
            _ed = self._entitiesDict(botState)
            _ed["custom"] = custom
            templatedRequestBody = Template(requestBody).render(_ed)
            #log.debug("templatedRequestBody (%s): %s", type(templatedRequestBody), templatedRequestBody)
            requestBodyJsonObject = json.loads(templatedRequestBody)

        urlPieces = six.moves.urllib.parse.urlparse(templatedURL)
        log.debug("urlPieces: %s" % (urlPieces,))
        response = {}
        if not (len(urlPieces.scheme) > 0 and len(urlPieces.netloc) > 0):
            raise Exception("bad api url: %s" % (templatedUrl,))

        requestAuthTuple = None
        if requestAuth:
            requestAuthTuple = tuple(requestAuth.split(":"))
            assert len(requestAuthTuple) == 2, "requestAuth must be a string with format username:password. (%s)" % (requestAuth,)

        requestHeaders = webhook.get("api_request_headers")
        if requestHeaders:
            requestHeaders = json.loads(requestHeaders)
        apiRequestType = webhook.get("api_request_type", "GET")
        if apiRequestType == "POST":  # "requestBodyJsonObject":
            log.info("making POST request: url: %s, json: %s, auth: %s",
                      templatedURL, requestBodyJsonObject, requestAuthTuple)
            response = requests.post(
                templatedURL, json=requestBodyJsonObject,
                headers=requestHeaders,
                auth=requestAuthTuple, timeout=timeoutSeconds)
        else:
            log.info("making GET request: url: %s, auth: %s",
                     templatedURL, requestAuthTuple)
            response = requests.get(
                templatedURL,
                headers=requestHeaders,
                auth=requestAuthTuple, timeout=timeoutSeconds)
        if response.status_code not in (200, 201, 202):
            log.exception("webhook call failed. status_code: %s", response.status_code)
            raise Exception("webhook call failed. status_code: %s" % (response.status_code,))
        log.info("response (%s): %s" % (type(response), response))
        responseJsonObj = {}
        try:
            responseJsonObj = response.json()
        except ValueError as ve:
            log.warn("could not get json from response to webhook")
        return responseJsonObj

    def doEmail(self, emailSpec, botState):
        d = self._entitiesDict(botState)
        toAddr = Template(emailSpec.get("to")).render(d)
        subject = Template(emailSpec.get("subject")).render(d)
        emailContent = Template(emailSpec.get("body")).render(d)
        r = keyframe.email.send(toAddr, subject, emailContent)
        responseContent = "<no response specified>"
        if r:
            responseContent = emailSpec.get("success_response")
        else:
            responseContent = emailSpec.get("failure_response")
        return Template(responseContent).render(d)

    def getAttachmentUrls(self, botState):
        urls = []
        sessionData = botState.getSessionData()
        for (k,v) in six.iteritems(botState.getSessionDataType()):
            if v == "ATTACHMENTS":
                url = sessionData.get(k)
                if url.lower() in ("no","none","no attachment"):
                    continue
                assert url, "Attachment does not have a url value (%s)" % (k,)
                urls.append(url)
        return urls

    def processZendesk(self, botState):
        log.info("processZendesk CALLED.")
        zendeskConfig = self.actionSpec.get("zendesk")
        log.debug("zendeskConfig: %s", zendeskConfig)
        log.debug("self.contactChannelsConfig: %s", self.contactChannelsConfig)
        zc = copy.deepcopy(zendeskConfig.get("request"))
        if not zc.get("api_host") and self.contactChannelsConfig and self.contactChannelsConfig.get("zendesk"):
            zc.update(self.contactChannelsConfig["zendesk"])
        if not zc.get("ticket_tags") and self.contactChannelsConfig and self.contactChannelsConfig.get("zendesk", {}).get("ticket_tags"):
            zc["ticket_tags"] = self.contactChannelsConfig.get("zendesk", {}).get("ticket_tags")

        _ed = self._entitiesDict(botState)
        for (k,v) in six.iteritems(zendeskConfig.get("request")):
            log.info("k: %s, v: %s", k, v)
            if v:
                zc[k] = Template(v).render(_ed)
        if zc.get("attachments"):
            if zc.get("attachments").lower() in (
                    "none", "no", "no attachments"):
                zc["attachments"] = None
            if zc.get("attachments").lower() == "all":
                attachmentUrls = self.getAttachmentUrls(botState)
                log.debug("attachmentUrls: %s", attachmentUrls)
                zc["attachments"] = attachmentUrls
            else:
                attachmentUrl = Template(zc.get("attachments")).render(_ed)
                zc["attachments"] = [attachmentUrl]
        if zc.get("ticket_tags"):
            # Zendesk does not allow spaces in tag strings - it will just make them different tags.
            #zc["ticket_tags"] = [e.strip().replace(" ", "_") for e in zc.get("ticket_tags").strip().split(",")]
            zc["ticket_tags"] = zc.get("ticket_tags").strip()

        zr = zendesk.createTicket(zc)
        log.debug("zr (%s): %s", type(zr), zr)
        respTemplate = "A ticket has been filed: {{ticket.agenturl}}"
        respTemplate = zendeskConfig.get("response_text", respTemplate)
        log.debug("respTemplate: %s", respTemplate)
        _t = Template(respTemplate)
        resp = _t.render(zr)
        log.debug("after processing zendesk, resp: %s", resp)
        return {
            "text": resp,
            "ticket_url": zr.get("ticket",{}).get("agenturl")
            }
        #return resp

    def processSalesforce(self, botState):
        salesforceConfig = self.actionSpec.get("salesforce")
        zc = copy.deepcopy(salesforceConfig.get("request"))
        if not zc.get("username") and self.contactChannelsConfig.get("salesforce"):
            zc.update(self.contactChannelsConfig["salesforce"])

        _ed = self._entitiesDict(botState)
        log.info("_ED: %s", _ed)
        for (k,v) in six.iteritems(salesforceConfig.get("request")):
            log.info("k: %s, v: %s", k, v)
            if v:
                zc[k] = Template(v).render(_ed)
                log.info("AFTER RENDERING, zc[k] value is: %s", zc[k])
        log.info("calling salesforce.createTicket")
        zr = salesforce.createTicket(zc)
        log.info("zr: %s", zr)
        respTemplate = "A ticket has been filed: {{ticket.url}}"
        respTemplate = salesforceConfig.get("response_text", respTemplate)
        log.info("respTemplate: %s", respTemplate)
        _t = Template(respTemplate)
        resp = _t.render(zr)
        log.debug("after processing zendesk, resp: %s", resp)
        return {
            "text": resp,
            "ticket_url": zr.get("ticket",{}).get("url")
            }
        #return resp

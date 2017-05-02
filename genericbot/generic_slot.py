import keyframe.slot_fill
import keyframe.dsl
import keyframe.messages

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
        assert self.promptMsg
        if self.entityType == "OPTIONS":
            return self.promptMsg
        return self.promptMsg

    def respond(self, text, canonicalMsg, responseType=None, botStateUid=None):
        log.debug("GenericSlot.respond(%s)", locals())

        cr = messages.createTextResponse(
            self.canonicalMsg,
            text,
            responseType,
            responseMeta=messages.ResponseMeta(
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
        self.filled = True
        return self.filled

class GenericActionSlot(keyframe.slot_fill.Slot):
    def __init__(self, apiResult=None, newTopic=None,
                 topicId=None, channelClient=None):
        super(GenericSlot, self).__init__(
            apiResult=apiResult, newTopic=newTopic,
            topicId=topicId)
        self.channelClient = channelClient
        self.actionSpec = None

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
        elif actionType == "email":
            resp = self.doStructuredResponse(
                self.actionSpec.get("email"))
        elif actionType == "webhook":
            resp = self.fetchWebhook(
                self.actionSpec.get("webhook"))
        else:
            raise Exception("Unknown actionType (%s)" % (actionType,))
        return self.respond(
            resp, canonicalMsg, botStateUid=botState.getUid())

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

    def processZendesk(self, botState):
        zc = copy.deepcopy(self.zendeskConfig.get("request"))
        for (k,v) in self.zendeskConfig.get("request").iteritems():
            log.debug("k: %s, v: %s", k, v)
            zc[k] = Template(v).render(
                {"entities":self.filledSlots})
        if zc.get("attachments"):
            if zc.get("attachments").lower() in (
                    "none", "no", "no attachments"):
                zc["attachments"] = None
            if zc.get("attachments").lower() == "all":
                attachmentUrls = self.getAttachmentUrls(
                    self.filledSlots, self.slotObjects)
                zc["attachments"] = attachmentUrls
            else:
                attachmentUrl = Template(zc.get("attachments")).render(
                    {"entities":self.filledSlots})
                zc["attachments"] = [attachmentUrl]
        zr = zendesk.createTicket(zc)
        log.debug("zr (%s): %s", type(zr), zr)
        respTemplate = "A ticket has been filed: {{ticket.url}}"
        respTemplate = self.zendeskConfig.get("response_text", respTemplate)
        log.debug("respTemplate: %s", respTemplate)
        _t = Template(respTemplate)
        resp = _t.render(zr)
        log.debug("after processing zendesk, resp: %s", resp)
        return resp

import keyframe.slot_fill
import keyframe.dsl
import keyframe.messages

class GenericSlot(keyframe.slot_fill.Slot):
    def __init__(self, apiResult=None, newIntent=None,
                 promptMsg=None, intentStr=None):
        super(GenericSlot, self).__init__(
            apiResult=apiResult, newIntent=newIntent, intentStr=intentStr)
        self.promptMsg = promptMsg

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


class GenericInfoSlot(GenericSlot):
    def __init__(self, apiResult=None, newIntent=None,
                 promptMsg=None, intentStr=None):
        super(GenericInfoSlot, self).__init__(
            apiResult=apiResult, newIntent=newIntent, intentStr=intentStr)

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
                newIntent=self.newIntent,
                intentStr=self.intentStr),
            botStateUid=botState.getUid(),
            inputExpected=False)
        channelClient.sendResponse(cr)
        self.filled = True
        return self.filled

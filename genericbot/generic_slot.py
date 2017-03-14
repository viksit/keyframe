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
            return self.promptMsg + "[]"
        return self.promptMsg


class GenericInfoSlot(GenericSlot):
    def __init__(self, apiResult=None, newIntent=None,
                 promptMsg=None, intentStr=None):
        super(GenericInfoSlot, self).__init__(
            apiResult=apiResult, newIntent=newIntent, intentStr=intentStr)

    def prompt(self):
        return self.promptMsg

    def fill(self, canonicalMsg, apiResult, channelClient):
        self.apiResult = apiResult
        self.channelClient = channelClient
        self.canonicalMsg = canonicalMsg
        self._createAndSendResponse(
            self.prompt(), channelClient,
            responseType=keyframe.messages.ResponseElement.RESPONSE_TYPE_RESPONSE)
        self.filled = True
        return self.filled

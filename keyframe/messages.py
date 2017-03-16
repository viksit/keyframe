CHANNEL_FB = "channel-fb"
CHANNEL_SLACK = "channel-slack"
CHANNEL_CMDLINE = "channel-cmdline"
CHANNEL_HTTP_REQUEST_RESPONSE = "channel-http-request-response"
CHANNEL_SCRIPT = "channel-script"

class ChannelMsg(object):
    def __init__(self, channel, httpType, body):
        self.channel = channel
        self.httpType = httpType
        self.body = body  # Contents of body will be some channel-specific structure.

    def __repr__(self):
        return "ChannelMsg(channel=%s, httpType=%s, body=%s)" % \
            (self.channel, self.httpType, self.body)

    def toJSON(self):
        return {
            "channel": self.channel,
            "httpType": self.httpType,
            "body": self.body
        }

class ChannelUserProfile(object):
    def __init__(self, userId, userName, firstName, lastName):
        self.userId = userId
        self.userName = userName
        self.firstName = firstName
        self.lastName = lastName

    def __repr__(self):
        return "ChannelUserProfile(userId=%s, userName=%s, firstName=%s, lastName-=%s)" % \
            (self.userId, self.userName, self.firstName, self.lastName)

    def toJSON(self):
        return {
            "userId": self.userId,
            "userName": self.userName,
            "firstName": self.firstName,
            "lastName": self.lastName
        }

class CanonicalMsg(object):
    # msg types cater to different types of input. For example, an option selected
    # via a drop down, or a date selected via a widget, or a button click.
    # The msg type will affect how it is processed.
    MSG_TYPE_FREETEXT = "msg_type_freetext"
    MSG_TYPE_SLOT_OPTION = "msg_type_slot_option"
    MSG_TYPES = [MSG_TYPE_FREETEXT, MSG_TYPE_SLOT_OPTION]

    def __init__(self, channel, httpType, userId, text,
                 actualName=None, rid=None, msgType=None):
        self.channel = channel
        self.httpType = httpType
        self.userId = userId
        self.text = text
        self.actualName = actualName
        self.rid = rid
        self.msgType = msgType
        if not self.msgType:
            self.msgType = self.MSG_TYPE_FREETEXT
        assert self.msgType in CanonicalMsg.MSG_TYPES


    def __repr__(self):
        return ("CanonicalMsg(channel=%s, httpType=%s, userId=%s, "
                "text=%s, rid=%s)") % \
            (self.channel, self.httpType, self.userId,
             self.text, self.rid)

    def toJSON(self):
        return {
            "channel": self.channel,
            "httpType": self.httpType,
            "userId": self.userId,
            "text": self.text
        }

class CanonicalResponse(object):
    """Must support a common way to represent data that can then
    be transformed to the suitable format for any channel.
    """
    def __init__(self, channel, userId, responseElements=[]):
        self.channel = channel
        self.userId = userId
        self.responseElements = responseElements

    def __repr__(self):
        res = "CanonicalResponse(channel=%s, userId=%s, responseElements=%s)" % \
            (self.channel, self.userId, self.responseElements)
        return res.encode("utf-8")

    def toJSON(self):
        return {
            "channel": self.channel,
            "userId": self.userId,
            "responseElements": map(lambda x: x.toJSON(), self.responseElements)
        }

class ResponseMeta(object):
    def __init__(self, apiResult=None, newIntent=None, intentStr=None,
                 actionObjectInstanceId=None):
        self.apiResult = apiResult
        self.newIntent = newIntent
        self.intentStr = intentStr
        self.actionObjectInstanceId = actionObjectInstanceId

    def __repr__(self):
        return "ResponseMeta(apiResult=%s, newIntent=%s, intentStr=%s, actionObjectInstanceId=%s)" % (
            self.apiResult, self.newIntent, self.intentStr, self.actionObjectInstanceId)

    def toJSON(self):
        d = None
        if self.apiResult:
            intentDict = {}
            entitiesDict = {}
            d = {"intent":intentDict, "entities":entitiesDict,
                 "raw":self.apiResult.api_response}
            i = self.apiResult.intent
            if i:
                intentDict["label"] = i.label
                intentDict["score"] = i.score
                e = self.apiResult.entities
                if e:
                    entitiesDict["entity_dict"] = e.entity_dict
        return {"apiResult":d,
                "newIntent":self.newIntent,
                "intentStr":self.intentStr,
                "actionObjectInstanceId":self.actionObjectInstanceId}

class ResponseElement(object):
    TYPE_TEXT = "text"
    TYPE_CAROUSEL = "carousel"
    TYPE_YESNOBUTTON = "yesnobutton"
    TYPE_OPTIONS = "options"

    RESPONSE_TYPE_RESPONSE = "response"
    RESPONSE_TYPE_CTA = "cta"
    RESPONSE_TYPE_QUESTION = "question"
    RESPONSE_TYPE_DEBUG = "debug"
    RESPONSE_TYPE_PRERESPONSE = "preresponse"
    RESPONSE_TYPE_TRANSITIONMSG = "transitionmsg"
    RESPONSE_TYPE_SLOTFILL = "slotfill"
    RESPONSE_TYPE_SLOTFILL_RETRY = "slotfillretry"

    DISPLAY_TYPE_TEXT = "text"
    DISPLAY_TYPE_DROPDOWN = "dropdown"
    DISPLAY_TYPE_BUTTON_LIST = "buttonlist"

    def __init__(self, type, text=None, carousel=None, responseType=None, responseMeta=None, optionsList=None, displayType=None):
        """
        text: Text response to show user
        carousel: To render a series of images on the channel
        responseType: response/cta/question/debug/preresponse
        responseMeta: metadata about the response
        """
        self.type = type
        self.text = text
        self.carousel = carousel
        self.responseType = responseType
        self.responseMeta = responseMeta
        self.optionsList = optionsList
        self.displayType = displayType

    def __repr__(self):
        res = "ResponseElement(type=%s, responseType=%s, text=%s, carousel=%s, optionsList=%s, responseMeta=%s)" % \
            (self.type, self.responseType, self.text, self.carousel, self.optionsList, self.responseMeta)
        return res.encode("utf-8")

    def toJSON(self):
        rm = None
        if self.responseMeta:
            rm = self.responseMeta.toJSON()
        return {
            "type": self.type,
            "responseType": self.responseType,
            "text": self.text,
            "carousel": self.carousel,
            "optionsList":self.optionsList,
            "responseMeta": rm,
            "displayType": self.displayType
        }

def createOptionsResponse(canonicalMsg, text, optionsList, responseType=None,
                          responseMeta=None, displayType=None):
    responseElement = ResponseElement(
        type=ResponseElement.TYPE_OPTIONS,
        optionsList=optionsList,
        text=text,
        responseType=responseType,
        responseMeta=responseMeta,
        displayType=displayType)
    return CanonicalResponse(
        channel=canonicalMsg.channel,
        userId=canonicalMsg.userId,
        responseElements=[responseElement])

        
def createTextResponse(canonicalMsg, text, responseType=None,
                       responseMeta=None):

    responseElement = ResponseElement(
        type=ResponseElement.TYPE_TEXT,
        text=text,
        responseType=responseType,
        responseMeta=responseMeta)
    return CanonicalResponse(
        channel=canonicalMsg.channel,
        userId=canonicalMsg.userId,
        responseElements=[responseElement])

def createYesNoButtonResponse(canonicalMsg, text, responseType=None):
    responseElement = ResponseElement(
        type=ResponseElement.TYPE_YESNOBUTTON,
        text=text,
        responseType=responseType)
    return CanonicalResponse(
        channel=canonicalMsg.channel,
        userId=canonicalMsg.userId,
        responseElements=[responseElement])

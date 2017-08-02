import utils
import logging

log = logging.getLogger(__name__)
#log.setLevel(10)

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
                 actualName=None, rid=None, msgType=None,
                 botStateUid=None):
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
        self.botStateUid = botStateUid

    def __repr__(self):
        return ("CanonicalMsg(channel=%s, httpType=%s, userId=%s, "
                "text=%s, rid=%s, botStateUid=%s)") % \
            (self.channel, self.httpType, self.userId,
             self.text, self.rid, self.botStateUid)

    def toJSON(self):
        return {
            "channel": self.channel,
            "httpType": self.httpType,
            "userId": self.userId,
            "text": self.text,
            "botStateUid": self.botStateUid
        }

class CanonicalResponse(object):
    """Must support a common way to represent data that can then
    be transformed to the suitable format for any channel.
    """
    def __init__(self, channel, userId, responseElements=[], botStateUid=None):
        self.channel = channel
        self.userId = userId
        self.responseElements = responseElements
        self.botStateUid = botStateUid

    def __repr__(self):
        res = "CanonicalResponse(channel=%s, userId=%s, responseElements=%s, botStateUid=%s)" % \
            (self.channel, self.userId, self.responseElements, self.botStateUid)
        return res.encode("utf-8")

    def toJSON(self):
        return {
            "channel": self.channel,
            "userId": self.userId,
            "responseElements": map(lambda x: x.toJSON(), self.responseElements),
            "botStateUid": self.botStateUid
        }

class ResponseMeta(object):
    def __init__(self, apiResult=None, newTopic=None, topicId=None,
                 actionObjectInstanceId=None):
        self.apiResult = apiResult
        self.newTopic = newTopic
        self.topicId = topicId
        self.actionObjectInstanceId = actionObjectInstanceId

    def __repr__(self):
        return "ResponseMeta(apiResult=%s, newTopic=%s, topicId=%s, actionObjectInstanceId=%s)" % (
            self.apiResult, self.newTopic, self.topicId, self.actionObjectInstanceId)

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
                "newTopic":self.newTopic,
                "topicId":self.topicId,
                "actionObjectInstanceId":self.actionObjectInstanceId}

class DisplaySearchPayload(object):
    def __init__(self, title, snippet, url):
        self.title = title
        self.snippet = snippet
        self.url = url

    def toJSON(self):
        return {"title": self.title,
                "snippet": self.snippet,
                "url": self.url}

    def __repr__(self):
        return json.dumps(self.toJSON())

class DisplayElement(object):
    TYPE_TEXT = "text"
    TYPE_TEXT_LIST = "textlist"
    TYPE_SEARCH_RESULT = "searchresult"

    def __init__(self, type, payload=None):
        self.type = type
        self.payload = payload

    def toJSON(self):
        return {"type": self.type,
                "payload": self.payload}

    def __repr__(self):
        return json.dumps(self.toJSON())

class InputElement(object):
    TYPE_TEXT = "text"
    TYPE_DROPDOWN = "dropdown"
    TYPE_BUTTONLIST = "buttonlist"
    TYPE_ATTACHMENTS = "attachments"
    TYPE_DISABLE = "disable"

    def __init__(self, type, options=None):
        self.type = type
        self.options = options

    def toJSON(self):
        return {"type": self.type,
                "options": self.options}

    def __repr__(self):
        return json.dumps(self.toJSON())


class ResponseElement(object):
    RESPONSE_TYPE_RESPONSE = "response"
    RESPONSE_TYPE_CTA = "cta"
    RESPONSE_TYPE_QUESTION = "question"
    RESPONSE_TYPE_DEBUG = "debug"
    RESPONSE_TYPE_PRERESPONSE = "preresponse"
    RESPONSE_TYPE_TRANSITIONMSG = "transitionmsg"
    RESPONSE_TYPE_SLOTFILL = "slotfill"
    RESPONSE_TYPE_SLOTFILL_RETRY = "slotfillretry"
    RESPONSE_TYPE_SEARCH_RESULTS = "searchresults"

    MSG_BREAK_TAG = "<msgbr>"

    def __init__(
            self,
            displayElement, inputElement, responseMeta,
            responseType, uuid=None):
        self.displayElement = displayElement
        self.inputElement = inputElement
        self.responseMeta = responseMeta
        self.responseType = responseType
        self.uuid = uuid
        if not self.uuid:
            self.uuid = utils.getUUID()

    def toJSON(self):
        return {"displayElement": _toJSON(self.displayElement),
                "inputElement": _toJSON(self.inputElement),
                "responseMeta": _toJSON(self.responseMeta),
                "responseType": self.responseType,
                "uuid": self.uuid}

def _toJSON(o):
    if not o:
        return None
    return o.toJSON()

class ResponseElementOld(object):
    # These are to tell the client the type of response
    # that is expected. It is related to the EntityType
    # (see generic_action.GenericActionObject.ENTITY_TYPE_CLASS_MAP),
    # but this is currently different to that.
    TYPE_TEXT = "text"
    TYPE_CAROUSEL = "carousel"
    TYPE_YESNOBUTTON = "yesnobutton"
    TYPE_OPTIONS = "options"
    TYPE_ATTACHMENTS = "attachments"

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

    MSG_BREAK_TAG = "<msgbr>"

    def __init__(self, type, text=None, carousel=None, responseType=None,
                 responseMeta=None, optionsList=None, displayType=None,
                 inputExpected=None, uuid=None,
                 textList=None, textType="single"):
        """
        text: Text response to show user
        carousel: To render a series of images on the channel
        responseType: response/cta/question/debug/preresponse
        responseMeta: metadata about the response
        """
        self.type = type
        self.text = text
        # textList and textType only apply for type=ResponseElement.TYPE_TEXT
        self.textList = textList
        self.textType = textType  # single or list

        self.carousel = carousel
        self.responseType = responseType
        self.responseMeta = responseMeta
        self.optionsList = optionsList
        self.displayType = displayType
        self.inputExpected = inputExpected
        self.uuid = uuid
        if not self.uuid:
            self.uuid = utils.getUUID()

    def __repr__(self):
        res = ("ResponseElement(type=%s, responseType=%s, text=%s, carousel=%s, "
               "optionsList=%s, responseMeta=%s, displayType=%s, inputExpected=%s, "
               "uuid=%s, textType=%s, textList=%s") % (
                   self.type, self.responseType, self.text,
                   self.carousel, self.optionsList, self.responseMeta,
                   self.displayType, self.inputExpected, self.uuid,
                   self.textType, self.textList)
        return res.encode("utf-8")

    def toJSON(self):
        rm = None
        if self.responseMeta:
            rm = self.responseMeta.toJSON()
        return {
            "type": self.type,
            "responseType": self.responseType,
            "text": self.text,
            "textList": self.textList,
            "textType": self.textType,
            "carousel": self.carousel,
            "optionsList":self.optionsList,
            "responseMeta": rm,
            "displayType": self.displayType,
            "inputExpected": self.inputExpected,
            "uuid": self.uuid
        }

def createOptionsResponse(canonicalMsg, text, optionsList, responseType=None,
                          responseMeta=None, displayType=None, botStateUid=None):
    displayElement = _createTextDisplayElement(text)
    inputElement = InputElement(
        type=displayType, options=optionsList)
    responseElement = ResponseElement(
        displayElement=displayElement,
        inputElement=inputElement,
        responseMeta=responseMeta,
        responseType=responseType)
    return CanonicalResponse(
        channel=canonicalMsg.channel,
        userId=canonicalMsg.userId,
        responseElements=[responseElement],
        botStateUid=botStateUid)

def createOptionsResponseOld(canonicalMsg, text, optionsList, responseType=None,
                          responseMeta=None, displayType=None, botStateUid=None):
    responseElement = ResponseElement(
        type=ResponseElement.TYPE_OPTIONS,
        optionsList=optionsList,
        text=text,
        responseType=responseType,
        responseMeta=responseMeta,
        displayType=displayType,
        inputExpected=True)
    return CanonicalResponse(
        channel=canonicalMsg.channel,
        userId=canonicalMsg.userId,
        responseElements=[responseElement],
        botStateUid=botStateUid)

        
def createAttachmentsResponse(canonicalMsg, text, responseType=None,
                              responseMeta=None, botStateUid=None):
    displayElement = _createTextDisplayElement(text)
    inputElement = InputElement(
        type=InputElement.TYPE_ATTACHMENTS)
    responseElement = ResponseElement(
        displayElement=displayElement,
        inputElement=inputElement,
        responseMeta=responseMeta,
        responseType=responseType)
    return CanonicalResponse(
        channel=canonicalMsg.channel,
        userId=canonicalMsg.userId,
        responseElements=[responseElement],
        botStateUid=botStateUid)

def createAttachmentsResponseOld(canonicalMsg, text, responseType=None,
                              responseMeta=None, botStateUid=None):
    responseElement = ResponseElement(
        type=ResponseElement.TYPE_ATTACHMENTS,
        text=text,
        responseType=responseType,
        responseMeta=responseMeta,
        inputExpected=True)
    return CanonicalResponse(
        channel=canonicalMsg.channel,
        userId=canonicalMsg.userId,
        responseElements=[responseElement],
        botStateUid=botStateUid)


def _createTextDisplayElement(text):
    textList = None
    type = DisplayElement.TYPE_TEXT
    x = text.split(ResponseElement.MSG_BREAK_TAG)
    if len(x) > 1:
        type = DisplayElement.TYPE_TEXT_LIST
        textList = [e.strip() for e in x]
    payload = {"text":text, "textList":textList}
    displayElement = DisplayElement(
        type=type, payload=payload)
    return displayElement

def createTextResponse(canonicalMsg, text, responseType=None,
                       responseMeta=None, botStateUid=None,
                       inputExpected=True):
    displayElement = _createTextDisplayElement(text)
    inputType = InputElement.TYPE_TEXT
    if not inputExpected:
        inputType = InputElement.TYPE_DISABLE
    inputElement = InputElement(
        type=inputType)
    responseElement = ResponseElement(
        displayElement=displayElement,
        inputElement=inputElement,
        responseMeta=responseMeta,
        responseType=responseType)
    return CanonicalResponse(
        channel=canonicalMsg.channel,
        userId=canonicalMsg.userId,
        responseElements=[responseElement],
        botStateUid=botStateUid)

def createSearchResponse(canonicalMsg, searchResults,
                         responseMeta=None, botStateUid=None):
    displayElement = DisplayElement(
        type=DisplayElement.TYPE_SEARCH_RESULT,
        payload=searchResults)
    inputElement = InputElement(
        type=InputElement.TYPE_DISABLE)
    responseElement = ResponseElement(
        displayElement=displayElement,
        inputElement=inputElement,
        responseMeta=responseMeta,
        responseType=ResponseElement.RESPONSE_TYPE_SEARCH_RESULTS)
    return CanonicalResponse(
        channel=canonicalMsg.channel,
        userId=canonicalMsg.userId,
        responseElements=[responseElement],
        botStateUid=botStateUid)


def createTextResponseOld(canonicalMsg, text, responseType=None,
                       responseMeta=None, botStateUid=None,
                       inputExpected=False):
    textList = None
    textType = "single"
    x = text.split(ResponseElement.MSG_BREAK_TAG)
    if len(x) > 1:
        textType = "list"
        textList = [e.strip() for e in x]
    log.debug("textType: %s, textList: %s", textType, textList)
    responseElement = ResponseElement(
        type=ResponseElement.TYPE_TEXT,
        text=text,
        textList=textList,
        textType=textType,
        responseType=responseType,
        responseMeta=responseMeta,
        inputExpected=inputExpected)
    return CanonicalResponse(
        channel=canonicalMsg.channel,
        userId=canonicalMsg.userId,
        responseElements=[responseElement],
        botStateUid=botStateUid)

def createYesNoButtonResponseOld(
        canonicalMsg, text, responseType=None, botStateUid=None):
    responseElement = ResponseElement(
        type=ResponseElement.TYPE_YESNOBUTTON,
        text=text,
        responseType=responseType,
        inputExpected=True)
    botState
    return CanonicalResponse(
        channel=canonicalMsg.channel,
        userId=canonicalMsg.userId,
        responseElements=[responseElement],
        botStateUid=botStateUid)

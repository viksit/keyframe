from __future__ import absolute_import
from . import utils
import logging
import six

log = logging.getLogger(__name__)
#log.setLevel(10)

CHANNEL_FB = "channel-fb"
CHANNEL_SLACK = "channel-slack"
CHANNEL_CMDLINE = "channel-cmdline"
CHANNEL_HTTP_REQUEST_RESPONSE = "channel-http-request-response"
CHANNEL_SCRIPT = "channel-script"
CHANNEL_INTERCOM = "channel-intercom"
CHANNEL_INTERCOM_MSG = "channel-intercom-msg"

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
    MSG_TYPE_EVENT = "msg_type_event"
    MSG_TYPES = [MSG_TYPE_FREETEXT, MSG_TYPE_SLOT_OPTION, MSG_TYPE_EVENT]

    def __init__(self, channel, httpType, userId, text,
                 actualName=None, rid=None, msgType=None,
                 botStateUid=None, customProps=None, locationHref=None,
                 userInfo=None, eventInfo=None, instanceId=None):
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
        self.customProps = customProps
        if self.customProps is None:
            self.customProps = {}
        self.locationHref = locationHref
        self.userInfo = userInfo
        self.eventInfo = eventInfo
        self.instanceId = instanceId

    def __repr__(self):
        # There is a problem with structs/objects containing unicode in sequences.
        # So this is required.
        customProps = self.customProps
        if customProps:
            customProps = "".join("%s:%s"%(k,v) for (k,v) in six.iteritems(customProps))
        return ("CanonicalMsg(channel=%s, httpType=%s, userId=%s, "
                "text=%s, rid=%s, botStateUid=%s, customProps=%s, "
                "locationHref=%s, userInfo=%s, eventInfo=%s, instanceId=%s)") % \
            (self.channel, self.httpType, self.userId,
             self.text, self.rid, self.botStateUid, customProps,
             self.locationHref, self.userInfo, self.eventInfo, self.instanceId)

    def toJSON(self):
        return {
            "channel": self.channel,
            "httpType": self.httpType,
            "userId": self.userId,
            "text": self.text,
            "botStateUid": self.botStateUid,
            "customProps": self.customProps,
            "locationHref": self.locationHref,
            "userInfo": self.userInfo,
            "eventInfo": self.eventInfo,
            "instanceId": self.instanceId
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
        log.debug("CanonicalResponse.__repr__")
        # ResponseElements are objects that may have unicode (non-ascii) strings.
        # Just doing "responseElements=%s" % (self.responseElements,) does not work.
        tmp1 = "responseElements=%s" % (["%s" % (e,) for e in self.responseElements],)
        log.debug("type(tmp1): %s", type(tmp1))
        res = "CanonicalResponse(channel=%s, userId=%s, %s, botStateUid=%s)" % \
            (self.channel, self.userId, tmp1, self.botStateUid)
        #return res.encode("utf-8")
        return res

    def toJSON(self):
        return {
            "channel": self.channel,
            "userId": self.userId,
            "responseElements": [x.toJSON() for x in self.responseElements],
            "botStateUid": self.botStateUid
        }

class ResponseMeta(object):
    def __init__(self, apiResult=None, newTopic=None, topicId=None,
                 actionObjectInstanceId=None, searchAPIResult=None,
                 zendeskTicketUrl=None):
        self.apiResult = apiResult
        self.newTopic = newTopic
        self.topicId = topicId
        self.actionObjectInstanceId = actionObjectInstanceId
        self.searchAPIResult = searchAPIResult
        self.zendeskTicketUrl = zendeskTicketUrl

    def __repr__(self):
        return "ResponseMeta(apiResult=%s, newTopic=%s, topicId=%s, actionObjectInstanceId=%s, searchAPIResult=%s, zendeskTicketUrl=%s)" % (
            self.apiResult, self.newTopic, self.topicId, self.actionObjectInstanceId, self.searchAPIResult, self.zendeskTicketUrl)

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
                "actionObjectInstanceId":self.actionObjectInstanceId,
                "searchAPIResult":self.searchAPIResult,
                "zendeskTicketUrl":self.zendeskTicketUrl}

class ResponseElement(object):
    # These are to tell the client the type of response
    # that is expected. It is related to the EntityType
    # (see generic_action.GenericActionObject.ENTITY_TYPE_CLASS_MAP),
    # but this is currently different to that.
    TYPE_TEXT = "text"
    TYPE_CAROUSEL = "carousel"
    TYPE_YESNOBUTTON = "yesnobutton"
    TYPE_OPTIONS = "options"
    TYPE_ATTACHMENTS = "attachments"
    TYPE_SEARCH_RESULT = "searchresult"
    TYPE_NEW_TOPIC = "newtopic"

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
                 textList=None, textType="single", structuredResults=None,
                 screenId=None):
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
        self.structuredResults = structuredResults
        self.screenId = screenId

    def __repr__(self):
        log.debug("ResponseElement.__repr__")
        res = ("ResponseElement(type=%s, responseType=%s, text=%s, carousel=%s, "
               "optionsList=%s, responseMeta=%s, displayType=%s, inputExpected=%s, "
               "uuid=%s, textType=%s, textList=%s, screenId=%s, structuredResults=%s") % (
                   self.type, self.responseType, self.text,
                   self.carousel, self.optionsList, self.responseMeta,
                   self.displayType, self.inputExpected, self.uuid,
                   self.textType, self.textList, self.screenId,
                   self.structuredResults)
        #r = res.encode("utf-8")
        r = res
        log.debug("ResponseElement.__repr__ returning %s (type: %s)", r, type(r))
        return r

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
            "uuid": self.uuid,
            "screenId": self.screenId,
            "structuredResults": self.structuredResults
        }

def createSearchResponse(canonicalMsg, searchResults, responseType=None,
                         responseMeta=None, displayType=None, botStateUid=None,
                         text=None):
    log.info("createSearchResponse(%s)", locals())
    responseElement = ResponseElement(
        type=ResponseElement.TYPE_SEARCH_RESULT,
        responseType=responseType,
        responseMeta=responseMeta,
        displayType=displayType,
        inputExpected=False,
        structuredResults=searchResults,
        text=text)
    return CanonicalResponse(
        channel=canonicalMsg.channel,
        userId=canonicalMsg.userId,
        responseElements=[responseElement],
        botStateUid=botStateUid)

def createNewTopicResponse(canonicalMsg, screenId, responseType=None,
                           responseMeta=None, displayType=None, botStateUid=None):
    responseElement = ResponseElement(
        type=ResponseElement.TYPE_NEW_TOPIC,
        screenId=screenId,
        responseType=responseType,
        responseMeta=responseMeta,
        displayType=displayType)
    return CanonicalResponse(
        channel=canonicalMsg.channel,
        userId=canonicalMsg.userId,
        responseElements=[responseElement],
        botStateUid=botStateUid)



def createOptionsResponse(canonicalMsg, text, optionsList, responseType=None,
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


def createTextResponse(canonicalMsg, text, responseType=None,
                       responseMeta=None, botStateUid=None,
                       inputExpected=False):
    log.debug("createTextResponse(%s)", locals())
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

def createYesNoButtonResponse(
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

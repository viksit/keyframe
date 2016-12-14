CHANNEL_FB = "channel-fb"
CHANNEL_CMDLINE = "channel-cmdline"
CHANNEL_HTTP_REQUEST_RESPONSE = "channel-http-request-response"

class ChannelMsg(object):
    def __init__(self, channel, httpType, body):
        self.channel = channel
        self.httpType = httpType
        self.body = body  # Contents of body will be some channel-specific structure.

    def __repr__(self):
        return "ChannelMsg(channel=%s, httpType=%s, body=%s)" % \
            (self.channel, self.httpType, self.body)

class ChannelUserProfile(object):
    def __init__(self, userId, userName, firstName, lastName):
        self.userId = userId
        self.userName = userName
        self.firstName = firstName
        self.lastName = lastName

    def __repr__(self):
        return "ChannelUserProfile(userId=%s, userName=%s, firstName=%s, lastName-=%s)" % \
            (self.userId, self.userName, self.firstName, self.lastName)

class CanonicalMsg(object):
    def __init__(self, channel, httpType, userId, text,
                 actualName=None):
        self.channel = channel
        self.httpType = httpType
        self.userId = userId
        self.text = text
        self.actualName = None

    def __repr__(self):
        return ("CanonicalMsg(channel=%s, httpType=%s, userId=%s, "
                "text=%s)") % \
            (self.channel, self.httpType, self.userId,
             self.text)

class CanonicalResponse(object):
    """Must support a common way to represent data that can then
    be transformed to the suitable format for any channel.
    """
    def __init__(self, channel, userId, responseElements=[]):
        self.channel = channel
        self.userId = userId
        self.responseElements = responseElements

    def __repr__(self):
        return "CanonicalResponse(channel=%s, userId=%s, responseElements=%s)" % \
            (self.channel, self.userId, self.responseElements)

class ResponseElement(object):
    TYPE_TEXT = "text"
    TYPE_CAROUSEL = "carousel"
    TYPE_YESNOBUTTON = "yesnobutton"

    RESPONSE_TYPE_RESPONSE = "response"
    RESPONSE_TYPE_CTA = "cta"
    RESPONSE_TYPE_QUESTION = "question"
    RESPONSE_TYPE_DEBUG = "debug"
    RESPONSE_TYPE_PRERESPONSE = "preresponse"

    def __init__(self, type, text=None, carousel=None, responseType=None):
        self.type = type
        self.text = text
        self.carousel = carousel
        self.responseType = responseType

    def __repr__(self):
        return "ResponseElement(type=%s, responseType=%s, text=%s, carousel=%s)" % \
            (self.type, self.responseType, self.text, self.carousel)


class ProcessedInputMsg(object):
    def __init__(self, intent, intentScore, entities):
        self.intent = intent
        self.intentScore = intentScore
        self.entities = entities

    def __repr__(self):
        return "%s" % (self.__dict__,)


def createTextResponse(canonicalMsg, text, responseType=None):
    responseElement = ResponseElement(
        type=ResponseElement.TYPE_TEXT,
        text=text,
        responseType=responseType)
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

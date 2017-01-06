CHANNEL_FB = "channel-fb"
CHANNEL_SLACK = "channel-slack"
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

class ResponseElement(object):
    TYPE_TEXT = "text"
    TYPE_CAROUSEL = "carousel"
    TYPE_YESNOBUTTON = "yesnobutton"

    RESPONSE_TYPE_RESPONSE = "response"
    RESPONSE_TYPE_CTA = "cta"
    RESPONSE_TYPE_QUESTION = "question"
    RESPONSE_TYPE_DEBUG = "debug"
    RESPONSE_TYPE_PRERESPONSE = "preresponse"

    def __init__(self, type, text=None, carousel=None, responseType=None, parseResult=None):
        """
        text: Text response to show user
        carousel: To render a series of images on the channel
        responseType: response/cta/question/debug/preresponse
        parseResult: raw output of the myra API
        """
        self.type = type
        self.text = text
        self.carousel = carousel
        self.responseType = responseType
        self.parseResult = parseResult

    def __repr__(self):
        res = "ResponseElement(type=%s, responseType=%s, text=%s, carousel=%s, parseResult=%s)" % \
            (self.type, self.responseType, self.text, self.carousel, self.parseResult)
        return res.encode("utf-8")

    def toJSON(self):
        return {
            "type": self.type,
            "responseType": self.responseType,
            "text": self.text,
            "carousel": self.carousel,
            "parseResult": self.parseResult
        }

def createTextResponse(canonicalMsg, text, responseType=None, apiResult=None):

    # WIP: Bubble the results of the myra api call into every canonical response
    # and response elements.
    # For this, we need to pass the intentObj into actionObject.create(), and also
    #
    # TODO(viksit)

    # print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    # print(">>>> API Result: ", apiResult)
    # print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
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

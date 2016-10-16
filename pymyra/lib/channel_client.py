#!/usr/local/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
import collections
import logging
import codecs

import messages
import bot_arch.fb

log = logging.getLogger(__name__)

class ChannelClientError(Exception):
    pass


class ChannelClient(object):
    def __init__(self, config=None):
        self.config = config

    def extract(self, channelMsg):
        raise NotImplementedError()

    def getChannelUserProfile(self, userId):
        """returns messages.ChannelUserProfile for userId
        """
        return None

    def sendResponse(self, canonicalResponse):
        raise NotImplementedError()

    def getResponses(self):
        return None

    def popResponses(self):
        return None

    def clearResponses(self):
        pass

class ChannelClientCmdline(ChannelClient):
    def extract(self, channelMsg):
        return messages.CanonicalMsg(
            channel=channelMsg.channel,
            httpType=channelMsg.httpType,
            userId=channelMsg.body.get("user_id"),
            text=channelMsg.body.get("text"))

    def sendResponse(self, canonicalResponse):
        for e in canonicalResponse.responseElements:
            print("\n\t>> ", e, "\n")


class ChannelClientFacebook(ChannelClient):
    def __init__(self, config=None):
        log.info("ChannelClientFacebook.__init__(%s)", locals())
        self.config = config
        self.responses = collections.deque()

    def getChannelUserProfile(self, userId):
        firstLastNameTuple = bot_arch.fb.get_user_name(
            userId, self.config.FB_PAGE_ACCESS_TOKEN)
        return messages.ChannelUserProfile(
            userId=userId,
            userName="%s %s" % (
                firstLastNameTuple[0],
                firstLastNameTuple[1]),
            firstName=firstLastNameTuple[0],
            lastName=firstLastNameTuple[1])

    def extract(self, channelMsg):
        if not channelMsg.body:
            return None
        x = bot_arch.fb.extract(channelMsg.body)
        if not x:
            return None
        (sender_id, text) = x
        actualName = None
        # TODO: user name should come from user profile,
        # not a call to FB for every request.
        if False:
            log.info("ChannelClientFacebook has config")
            if self.config.FB_PAGE_ACCESS_TOKEN:
                log.info("ChannelClientFacebook has access token")
                actualNameTuple = bot_arch.fb.get_user_name(
                    sender_id, self.config.FB_PAGE_ACCESS_TOKEN)
                if actualNameTuple:
                    actualName = " ".join(actualNameTuple)
        return messages.CanonicalMsg(
            channel=channelMsg.channel,
            httpType=channelMsg.httpType,
            userId=sender_id,
            text=text,
            actualName=actualName)

    def sendResponse(self, canonicalResponse):
        log.info("sendResponse(%s)", canonicalResponse)
        for rElem in canonicalResponse.responseElements:
            fbFormattedJsonObject = None
            if rElem.type == messages.ResponseElement.TYPE_TEXT:
                fbFormattedJsonObject = bot_arch.fb.response_text(
                    canonicalResponse.userId,
                    rElem.text)
            elif rElem.type == messages.ResponseElement.TYPE_CAROUSEL:
                fbFormattedJsonObject = bot_arch.fb.response_carousel(
                    canonicalResponse.userId,
                    rElem.carousel)
            elif rElem.type == messages.ResponseElement.TYPE_YESNOBUTTON:
                fbFormattedJsonObject = bot_arch.fb.response_yesnobutton(
                    canonicalResponse.userId,
                    rElem.text)
            bot_arch.fb.send(
                fbFormattedJsonObject, self.config.FB_PAGE_ACCESS_TOKEN)
            self.responses.append(fbFormattedJsonObject)

    def getResponses(self):
        ret = [r for r in self.responses]
        log.info("getResponses called, returning: %s", ret)
        return ret

    def popResponses(self):
        ret = self.getResponses()
        self.clearResponses()
        return ret

    def clearResponses(self):
        self.responses.clear()


class ChannelClientKeepResponses(ChannelClient):
    def __init__(self, config=None):
        log.info("ChannelClientKeepResponses.__init__(%s)", locals())
        self.config = config
        self.responses = collections.deque()

    def extract(self, channelMsg):
        return messages.CanonicalMsg(
            channel=channelMsg.channel,
            httpType=channelMsg.httpType,
            userId=channelMsg.body.get("user_id"),
            text=channelMsg.body.get("text"))

    def sendResponse(self, canonicalResponse):
        log.info("sendResponse(%s)", canonicalResponse)
        self.responses.append(canonicalResponse)

    def getResponses(self):
        ret = [r for r in self.responses]
        log.info("getResponses called, returning: %s", ret)
        return ret

    def popResponses(self):
        ret = self.getResponses()
        self.clearResponses()
        return ret

    def clearResponses(self):
        self.responses.clear()


channelClientMap = {
    messages.CHANNEL_CMDLINE:ChannelClientCmdline,
    messages.CHANNEL_HTTP_REQUEST_RESPONSE:
    ChannelClientKeepResponses,
    messages.CHANNEL_FB:ChannelClientFacebook
    }

def getChannelClient(channel, requestType, config=None):
    logging.info("getChannelClient(%s)", locals())
    x = channelClientMap.get(channel)
    if not x:
        raise ChannelClientError(
            "no matching channel client for channel=%s, requestType=%s" % (
                channel, requestType))
    if not isinstance(x, dict):
        return x(config=config)
    x2 = x.get(requestType)
    if not x2:
        raise ChannelClientError(
            "no matching channel client for channel=%s, requestType=%s" % (
                channel, requestType))
    return x2(config=config)

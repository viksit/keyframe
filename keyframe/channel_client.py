#!/usr/local/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
import collections
import logging
import codecs
import json

import messages
import fb
from slackclient import SlackClient

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
            text=channelMsg.body.get("text"),
            rid=channelMsg.body.get("rid"),
            botStateUid=channelMsg.body.get("bot_state_uid")
        )

    def sendResponse(self, canonicalResponse):
        print("\n>>\n", canonicalResponse.toJSON(), "\n")
        # for e in canonicalResponse.responseElements:
        #     print("\n>>\n", e.toJSON(), "\n")


class ChannelClientFacebook(ChannelClient):
    def __init__(self, config=None):
        log.info("ChannelClientFacebook.__init__(%s)", locals())
        self.config = config
        self.responses = collections.deque()

    def getChannelUserProfile(self, userId):
        firstLastNameTuple = fb.get_user_name(
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
        x = fb.extract(channelMsg.body)
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
                actualNameTuple = fb.get_user_name(
                    sender_id, self.config.FB_PAGE_ACCESS_TOKEN)
                if actualNameTuple:
                    actualName = " ".join(actualNameTuple)
        return messages.CanonicalMsg(
            channel=channelMsg.channel,
            httpType=channelMsg.httpType,
            userId=sender_id,
            text=text,
            actualName=actualName,
            rid=channelMsg.body.get("rid")
        )

    def sendResponse(self, canonicalResponse):
        log.debug("sendResponse(%s)", canonicalResponse)
        for rElem in canonicalResponse.responseElements:
            fbFormattedJsonObject = None
            if rElem.type == messages.ResponseElement.TYPE_TEXT:
                fbFormattedJsonObject = fb.response_text(
                    canonicalResponse.userId,
                    rElem.text)
            elif rElem.type == messages.ResponseElement.TYPE_CAROUSEL:
                fbFormattedJsonObject = fb.response_carousel(
                    canonicalResponse.userId,
                    rElem.carousel)
            elif rElem.type == messages.ResponseElement.TYPE_YESNOBUTTON:
                fbFormattedJsonObject = fb.response_yesnobutton(
                    canonicalResponse.userId,
                    rElem.text)
            fb.send(
                fbFormattedJsonObject, self.config.FB_PAGE_ACCESS_TOKEN)
            self.responses.append(fbFormattedJsonObject)

    def getResponses(self):
        ret = [r for r in self.responses]
        log.debug("getResponses called, returning: %s", ret)
        return ret

    def popResponses(self):
        ret = self.getResponses()
        self.clearResponses()
        return ret

    def clearResponses(self):
        self.responses.clear()


# channel_slack will contain helper functions for this to work
# for now we put this here.

class ChannelClientSlack(ChannelClient):
    def __init__(self, config=None):
        log.info("Init ChannelClientSlack.__init__(%s)", locals())
        self.config = config
        self.responses = collections.deque()
        self.userId = config.CHANNEL_META.get("user_id")
        self.teamId = config.CHANNEL_META.get("team_id")
        self.botToken = config.CHANNEL_META.get("bot_token")
        self.msgChannel = config.CHANNEL_META.get("msg_channel")

    def extract(self, channelMsg):
        log.info("extract(%s)", channelMsg)
        return messages.CanonicalMsg(
            channel=channelMsg.channel,
            httpType=channelMsg.httpType,
            userId=self.userId,
            text=channelMsg.body.get("event", {}).get("text"),
            rid=channelMsg.body.get("rid")
        )

    def sendResponse(self, canonicalResponse):
        slackClient = SlackClient(self.botToken)
        #new_dm = slackClient.api_call(
        #    "im.open",
        #    user=self.userId)
        #dm_id = new_dm["channel"]["id"]
        for e in canonicalResponse.responseElements:
            slackClient.api_call("chat.postMessage",
                                 channel=self.msgChannel,
                                 #channel=dm_id,
                                 #username="concierge",
                                 icon_emoji=":robot_face:",
                                 text=e.text)
            log.info("sendResponse(%s)", canonicalResponse)
            self.responses.append(canonicalResponse)

    def getResponses(self):
        ret = [r.toJSON() for r in self.responses]
        log.info("getResponses called, returning: %s", ret)
        return ret

    def popResponses(self):
        ret = self.getResponses()
        self.clearResponses()
        return ret

    def clearResponses(self):
        self.responses.clear()


class ChannelClientRESTAPI(ChannelClient):
    def __init__(self, config=None):
        log.info("ChannelClientRESTAPI.__init__(%s)", locals())
        self.config = config
        self.responses = collections.deque()

    def _extractEventInfo(self, channelMsg):
        eventType = channelMsg.body.get("event_type")
        if not eventType:
            return {}
        if eventType == "kb_click":
            return {
                "event_type": eventType,
                "target_href": channelMsg.body.get("target_href"),
                "target_title": channelMsg.body.get("target_title")}
        elif eventType == "workflow_click":
            return {
                "event_type": eventType,
                "target_title": channelMsg.body.get("target_title"),
                "target_href": channelMsg.body.get("workflow_text")
            }
        elif eventType == "url_click":
            return {
                "event_type": eventType,
                "target_href": channelMsg.body.get("target_href"),
                "target_title": channelMsg.body.get("target_title")}
        elif eventType == "support_click":
            return {
                "event_type": eventType,
                "target_href": channelMsg.body.get("target_href")}
        else:
            raise Exception("Unknown eventType: %s", eventType)

    def extract(self, channelMsg):
        log.debug("extract(%s)", channelMsg)
        msgType = None
        if channelMsg.body.get("event_type"):
            msgType = messages.CanonicalMsg.MSG_TYPE_EVENT
        userInfo = channelMsg.body.get("user_info", {})
        if not userInfo.get("user_id"):
            userInfo["user_id"] = channelMsg.body.get("user_id")
        instanceId = channelMsg.body.get("instance_id")
        if not instanceId:
            instanceId = "default_iid"
        return messages.CanonicalMsg(
            channel=channelMsg.channel,
            httpType=channelMsg.httpType,
            userId=channelMsg.body.get("user_id"),
            text=channelMsg.body.get("text"),
            rid=channelMsg.body.get("rid"),
            msgType=msgType,
            botStateUid=channelMsg.body.get("bot_state_uid"),
            customProps=channelMsg.body.get("custom_props"),
            locationHref=channelMsg.body.get("current_url"),
            userInfo=channelMsg.body.get("user_info"),
            eventInfo=self._extractEventInfo(channelMsg),
            instanceId=instanceId
        )

    def sendResponse(self, canonicalResponse):
        log.debug("sendResponse(%s)", canonicalResponse)
        self.responses.append(canonicalResponse)

    def getResponses(self):
        ret = [r.toJSON() for r in self.responses]
        log.debug("getResponses called, returning: %s", ret)
        return ret

    def popResponses(self):
        ret = self.getResponses()
        self.clearResponses()
        return ret

    def clearResponses(self):
        self.responses.clear()

class ChannelClientScript(ChannelClientRESTAPI):
    def getResponses(self):
        # Just get the response objects back vs json as for base class.
        ret = [r for r in self.responses]
        log.debug("getResponses called, returning: %s", ret)
        return ret


channelClientMap = {
    messages.CHANNEL_CMDLINE: ChannelClientCmdline,
    messages.CHANNEL_HTTP_REQUEST_RESPONSE: ChannelClientRESTAPI,
    messages.CHANNEL_FB: ChannelClientFacebook,
    messages.CHANNEL_SLACK: ChannelClientSlack,
    messages.CHANNEL_SCRIPT: ChannelClientScript
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

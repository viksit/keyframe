#!/usr/local/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import
import sys
import collections
import logging
import codecs
import json
from bs4 import BeautifulSoup

from . import messages
from . import fb
from slackclient import SlackClient
from .intercom_client import IntercomClient
from . import intercom_messenger
from . import imlib
from . import utils

log = logging.getLogger(__name__)

class ChannelClientError(Exception):
    pass

class ChannelClient(object):
    def __init__(self, config=None):
        self.config = config
        #self.channelMeta = {}

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


class ChannelClientReturnResponse(ChannelClient):
    def __init__(self, config=None):
        log.info("ChannelClientRESTAPI.__init__(%s)", locals())
        self.config = config
        self.responses = collections.deque()

    def sendResponse(self, canonicalResponse):
        log.debug("sendResponse(%s)", canonicalResponse)
        self.responses.append(canonicalResponse)

    def getResponses(self):
        # Just get the response objects back vs json as for base class.
        ret = [r for r in self.responses]
        log.debug("getResponses called, returning: %s", ret)
        return ret

    def popResponses(self):
        ret = self.getResponses()
        self.clearResponses()
        return ret

    def clearResponses(self):
        self.responses.clear()

class ChannelClientRESTAPI(ChannelClientReturnResponse):
    def __init__(self, config=None):
        super(ChannelClientRESTAPI, self).__init__(config)

    def getResponses(self):
        ret = [r.toJSON() for r in self.responses]
        log.debug("getResponses called, returning: %s", ret)
        return ret

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
        elif eventType == "widget_close_click":
            return {
                "event_type": eventType
                }
        elif eventType == "widget_cta_click":
            return {
                "event_type": eventType
                }
        else:
            raise Exception("Unknown eventType: %s" % (eventType,))

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


class ChannelClientScript(ChannelClientRESTAPI):
    pass

class ChannelClientIntercom(ChannelClientReturnResponse):
    def __init__(self, config=None):
        log.info("Init ChannelClientIntercom__init__(%s)", locals())
        super(ChannelClientIntercom, self).__init__(config)
        #self.channelMeta = config.CHANNEL_META
        # TODO(viksit): add user/team ids
        self.userId = config.CHANNEL_META.get("user_id")
        self.conversationId = config.CHANNEL_META.get("conversation_id")
        # userAccessToken enables responses to a particular clients conversion.
        # I.e. it is the intercom token allowing api access for the client the bot is responding on behalf of.
        self.userAccessToken = config.CHANNEL_META.get("access_token")
        self.supportAdminId = config.CHANNEL_META.get("support_admin_id")
        self.proxyAdminId = config.CHANNEL_META.get("proxy_admin_id")

    def extract(self, channelMsg):
        log.info("extract(%s)", channelMsg)
        text = channelMsg.body.get("data").get("item").get("conversation_message").get("body")
        convParts = channelMsg.body.get("data").get("item").get("conversation_parts").get("conversation_parts")
        if len(convParts) > 0 and convParts[0].get("body"):
            text = convParts[0].get("body")
        text = text.replace("<p>","").replace("</p>","")
        #conversationId = channelMsg.body.get("data", {}).get("item", {}).get("id")
        log.info("intercom extracted text: %s", text)
        return messages.CanonicalMsg(
            channel=channelMsg.channel,
            httpType=channelMsg.httpType,
            userId=self.userId,
            text=text,
            rid=channelMsg.body.get("id"),
            # For intercom, there aren't separate instances of the widget.
            # But there are different conversation ids.
            # Overload instanceId with conversationId.
            instanceId=self.conversationId
        )

    def sendResponse(self, canonicalResponse):
        intercomClient = IntercomClient(
            accessToken=self.userAccessToken)
        for e in canonicalResponse.responseElements:
            if e.type == messages.ResponseElement.TYPE_NEW_TOPIC:
                log.info("no new topic response for intercom channel")
                continue
            if not e.text:
                continue
            conversationId = self.conversationId
            intercomClient.sendResponse(text=e.text, conversationId=conversationId)
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


class ChannelClientIntercomMsg(ChannelClientReturnResponse):
    def __init__(self, config=None):
        log.info("Init ChannelClientIntercomMsg__init__(%s)", locals())
        super(ChannelClientIntercomMsg, self).__init__(config)
        self.userId = config.CHANNEL_META.get("user_id")
        self.conversationId = config.CHANNEL_META.get("conversation_id")
        self.storedData = {}

    def extract(self, channelMsg):
        log.info("extract(%s)", channelMsg)
        text = intercom_messenger.getInputFromAppRequest(channelMsg.body)
        log.info("extracted text from intercom msg: %s", text)
        return messages.CanonicalMsg(
            channel=channelMsg.channel,
            httpType=channelMsg.httpType,
            userId=self.userId,
            text=text,
            rid=channelMsg.body.get("id"),
            # For intercom msg, there doesn't seem to be anything to use as conversationId.
            instanceId=self.conversationId
        )

    def extract2(self, channelMsg):
        log.info("extract(%s)", channelMsg)
        # TODO: how do we extract the right text?
        _d = channelMsg.body.get("input_values", {})
        text = " ".join(v.strip() for (k,v) in _d.items())
        #text = channelMsg.body.get("input_values", {}).get("text")
        log.info("intercom extracted text: %s", text)
        if channelMsg.body.get("component_id") == "user_question":
            text = "[topic=default] %s" % (text,)
            log.info("reset agent with text: %s", text)
        return messages.CanonicalMsg(
            channel=channelMsg.channel,
            httpType=channelMsg.httpType,
            userId=self.userId,
            text=text,
            rid=channelMsg.body.get("id"),
            # For intercom msg, there doesn't seem to be anything to use as conversationId.
            instanceId=self.conversationId
        )

    def _addC(self, responses, c):
        if isinstance(c, list):
            responses.extend(c)
        else:
            responses.append(c)

    def sendResponse(self, canonicalResponse):
        log.info("ChannelClientIntercomMsg.sendResponse(%s)", canonicalResponse)
        for rElem in canonicalResponse.responseElements:
            # Must use uuid because id needs to be unique across multiple calls.
            eId = utils.getUUID()
            log.info("rElem: %s", rElem)
            if not rElem.responseType or rElem.responseType == "response":
                if rElem.type == messages.ResponseElement.TYPE_TEXT:
                    log.info("TYPE_TEXT")
                    t = rElem.text
                    if rElem.textList:
                        t = ' '.join(e.strip() for e in rElem.textList)
                    t = BeautifulSoup(t, "html.parser").text
                    c = intercom_messenger.getTextComponent(
                        text=t, id=f"text_response_{eId}")
                    self._addC(self.responses, c)

            if rElem.responseType in ("slotfill", "slotfillretry") or rElem.type == messages.ResponseElement.TYPE_SEARCH_RESULT:
                if rElem.type == messages.ResponseElement.TYPE_TEXT:
                    log.info("TYPE_TEXT")
                    t = rElem.text
                    if rElem.textList:
                        t = ' '.join(e.strip() for e in rElem.textList)
                    t = BeautifulSoup(t, "html.parser").text
                    c = intercom_messenger.getTextInputComponent(
                        label=t, id=f"text_slotfill_{eId}")
                    self._addC(self.responses, c)
                elif rElem.type == messages.ResponseElement.TYPE_OPTIONS:
                    log.info("TYPE_OPTIONS")
                    t = rElem.text
                    if rElem.textList:
                        t = ' '.join(e.strip() for e in rElem.textList)
                    t = BeautifulSoup(t, "html.parser").text
                    if t:
                        c = intercom_messenger.getTextComponent(
                            t, id=f"options_slotfill_{eId}")
                        self._addC(self.responses, c)
                    if rElem.displayType == messages.ResponseElement.DISPLAY_TYPE_BUTTON_LIST:
                        c = intercom_messenger.getButtonComponent(
                            values=rElem.optionsList)
                        self._addC(self.responses, c)
                    elif rElem.displayType == messages.ResponseElement.DISPLAY_TYPE_DROPDOWN:
                        c = intercom_messenger.getSingleSelectComponent(
                            label=t, values=rElem.optionsList)
                        self._addC(self.responses, c)
                    elif rElem.displayType == messages.ResponseElement.DISPLAY_TYPE_TEXT:
                        v = "[" + "|".join(eElem.optionsList) + "]"
                        c = intercom_messenger.getTextInputComponent(
                            label=t, placeholder=v)
                        self._addC(self.responses, c)
                        #raise NotImplementedError("options as text are not supported as yet")
                elif rElem.type == messages.ResponseElement.TYPE_SEARCH_RESULT:
                    log.info("NOW FORMATTING SEARCH RESULTS")
                    aList = []
                    for sr in rElem.structuredResults:
                        if sr.get("doctype") == "kb":
                            snippet = sr.get("snippets")
                            if not snippet:
                                snippet = ""
                            else:
                                snippet = snippet[0]
                            snippet = BeautifulSoup(snippet, "html.parser").text
                            aList.append({"url":sr.get("url"), "title":sr.get("title"),
                                          "type":"kb", "snippet":snippet})
                        elif sr.get("doctype") == "workflow":
                            snippet = sr.get("body")
                            if snippet:
                                snippet = BeautifulSoup(snippet, "html.parser").text
                            aList.append(
                                {"type":"workflow", "title":sr.get("title") + " [wf]",
                                 "workflowid":sr.get("workflowid"), "snippet":snippet})
                        else:
                            raise Exception("Unknown doctype: %s" % (sr.get("doctype"),))
                    r = intercom_messenger.getListComponent(aList)
                    self._addC(self.responses, r.get("component"))
                    self.storedData = r.get("stored_data")
                else:
                    raise NotImplementedError("Element type %s is not implemented" % (rElem.type,))
            else:
                # all of the rest are probably fine to just drop
                log.info("DROPPING responseElement: %s", rElem)
                if rElem.type == messages.ResponseElement.TYPE_NEW_TOPIC:
                    log.info("dropping type newtopic")
                    continue
                else:
                    continue

        log.info("self.responses: %s", self.responses)

    def getResponses(self):
        c = imlib.Canvas(
            content=imlib.Content(
                components=[r for r in self.responses]),
            stored_data=self.storedData)
        ret = imlib.makeResponse(c)
        log.info("getResponses called, returning: %s", ret)
        return ret


channelClientMap = {
    messages.CHANNEL_CMDLINE: ChannelClientCmdline,
    messages.CHANNEL_HTTP_REQUEST_RESPONSE: ChannelClientRESTAPI,
    messages.CHANNEL_FB: ChannelClientFacebook,
    messages.CHANNEL_SLACK: ChannelClientSlack,
    messages.CHANNEL_SCRIPT: ChannelClientScript,
    messages.CHANNEL_INTERCOM: ChannelClientIntercom,
    messages.CHANNEL_INTERCOM_MSG: ChannelClientIntercomMsg
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

from __future__ import print_function
from __future__ import absolute_import
import inspect
import logging

from . import messages
from . import channel_client
from . import fb
from . import config
from . import slot_fill
import copy

import uuid
from collections import defaultdict
import sys

log = logging.getLogger(__name__)

class BotAPI(object):
    """
    Class that allows this bot to be called via a flask API. This can be deployed
    wherever
    """
    def __init__(self, *args, **kwargs):
        self.channelClient = kwargs.get("channelClient")
        self.args = args
        self.kwargs = kwargs
        self.init()

    def init(self):
        pass

    def createAndSendTextResponse(self, canonicalMsg, text, responseType=None):
        cr = messages.createTextResponse(canonicalMsg, text, responseType)
        self.channelClient.sendResponse(cr)

    def handleMsg(self, channelMsg):
        """Handle the input message from all channels.
        Input
          inputMsg: (messages.ChannelMsg)
        Returns
          nothing
        """
        canonicalMsg = self.channelClient.extract(
            channelMsg=channelMsg)
        if not canonicalMsg:
            log.warn("no canonicalMsg extracted from channelMsg (%s)", channelMsg)
            return
        log.debug("created canonicalMsg: %s", canonicalMsg)
        # The bot to be created may depend on the user.
        bot = self.getBot()
        log.info("got bot: %s", bot)
        bot.setChannelClient(self.channelClient)
        log.info("now calling process on the bot with canonicalMsg.text: %s",
                 canonicalMsg.text)
        bot.process(canonicalMsg)

    def getBot(self):
        return self.bot

    @classmethod
    def getChannelClient(cls):
        channelClient = channel_client.ChannelClient()
        return channelClient

    @classmethod
    def requestHandler(cls, event, context):
        log.info("event: %s, context: %s",
                 event, context)

        # Check if this is a GET request from FB. If yes, it is a verify.
        # Handle it.
        if event.get("channel") == messages.CHANNEL_FB \
           and event.get("request-type") == "GET":
            return fb.gateway_webhook_verify_handler(
                event, context)

        channelMsg = messages.ChannelMsg(
            channel=event.get("channel"),
            httpType=event.get("request-type"),
            body=event.get("body"))

        channelClient = channel_client.getChannelClient(
            channel=event.get("channel"),
            requestType=event.get("request-type"),
            config=config.Config())

        botAPI = cls(
            channelClient=channelClient
        )
        botAPI.handleMsg(channelMsg)
        resp = channelClient.popResponses()
        log.info("BotAPI.requestHandler returning: %s", resp)
        return resp

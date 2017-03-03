from __future__ import print_function
import inspect
import copy
import uuid
from collections import defaultdict
import sys

import logging

import keyframe.messages
import keyframe.channel_client
import keyframe.fb
import keyframe.config
#import keyframe.slot_fill
import keyframe.bot_api

log = logging.getLogger(__name__)
# If want extra logging for this specific module, set it explicitly here.
#log.setLevel(10)

class GenericBotAPI(keyframe.bot_api.BotAPI):
    """
    Class that allows this bot to be called via a flask API. This can be deployed
    wherever
    """
    def __init__(self, *args, **kwargs):
        super(GenericBotAPI, self).__init__(*args, **kwargs)

    def getBot(self):
        return self.bot

    @classmethod
    def requestHandler(cls, event, context):
        log.info("event: %s, context: %s",
                 event, context)

        # Check if this is a GET request from FB. If yes, it is a verify.
        # Handle it.
        if event.get("channel") == keyframe.messages.CHANNEL_FB \
           and event.get("request-type") == "GET":
            return keyframe.fb.gateway_webhook_verify_handler(
                event, context)

        channelMsg = keyframe.messages.ChannelMsg(
            channel=event.get("channel"),
            httpType=event.get("request-type"),
            body=event.get("body"))

        cfg = keyframe.config.getConfig()
        cfg.CHANNEL_META = event.get("channel-meta")

        channelClient = keyframe.channel_client.getChannelClient(
            channel=event.get("channel"),
            requestType=event.get("request-type"),
            config=cfg)

        botAPI = cls(
            channelClient=channelClient
        )
        log.debug("calling botAPI.handleMsg(%s)", channelMsg)
        botAPI.handleMsg(channelMsg)
        resp = channelClient.popResponses()
        log.info("BotAPI.requestHandler returning: %s", resp)
        return resp

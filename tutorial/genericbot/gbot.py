from __future__ import print_function
import sys
from os.path import expanduser, join
from flask import Flask, request, Response

from pymyra.api import client

from keyframe.cmdline import BotCmdLineHandler
from keyframe.base import BaseBot
from keyframe.actions import ActionObject
from keyframe.slot_fill import Slot
from keyframe.bot_api import BotAPI
from keyframe import channel_client
from keyframe import messages
from keyframe import config
from keyframe import store_api
from keyframe import generic_bot

# TODO:
# Initialize via a configuration file
kvStore = store_api.get_kv_store(
    store_api.TYPE_LOCALFILE,
    #store_api.TYPE_DYNAMODB,
    #store_api.TYPE_INMEMORY,
    config.Config())


# TODO: This should get a json file for all the config in the future.
bot = generic_bot.GenericBot(kvStore=kvStore)


# Deployment for command line
class GenericCmdlineHandler(BotCmdLineHandler):
    def init(self):
        # channel configuration
        cf = config.Config()
        channelClient = channel_client.getChannelClient(
            channel=messages.CHANNEL_CMDLINE,
            requestType=None,
            config=cf)
        self.bot = bot
        bot.setChannelClient(channelClient)


# Deployment for command line
class CalendarCmdlineHandler(BotCmdLineHandler):
    def init(self):
        # channel configuration
        cf = config.Config()
        channelClient = channel_client.getChannelClient(
            channel=messages.CHANNEL_CMDLINE,
            requestType=None,
            config=cf)
        self.bot = bot
        bot.setChannelClient(channelClient)

if __name__ == "__main__":
    # Run the command line version
    c = CalendarCmdlineHandler()
    c.begin()


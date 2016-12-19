from __future__ import print_function
import sys, os
from os.path import expanduser, join
from flask import Flask, request, Response
import json
import logging

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

logging.basicConfig()
log = logging.getLogger()
log.setLevel(10)

# apicfg = {
#     "account_id": "1so4xiiNq29ElrbiONSsrS",
#     "account_secret": "a33efcebdc44f243aac4bfcf7bbcc24c29c90587",
#     "hostname": "api.dev.myralabs.com"
# }

# TODO: This is a dev config. Need to use a prod config.
apicfg = {
    "account_id": "BIRsNx4aBt9nNG6TmXudl",
    "account_secret": "f947dee60657b7df99cceaecc80dd4d644a5e3bd",
    "hostname": "api.dev.myralabs.com"
}

# TODO:
# Initialize via a configuration file
kvStore = store_api.get_kv_store(
    store_api.TYPE_LOCALFILE,
    #store_api.TYPE_DYNAMODB,
    #store_api.TYPE_INMEMORY,
    config.Config())


# TODO: This should get a json file for all the config in the future.
#bot = generic_bot.GenericBot(kvStore=kvStore)


# Deployment for command line
class GenericCmdlineHandler(BotCmdLineHandler):
    def init(self):
        log.debug("GenericCmdlineHandler.init")
        # channel configuration
        cf = config.Config()
        channelClient = channel_client.getChannelClient(
            channel=messages.CHANNEL_CMDLINE,
            requestType=None,
            config=cf)
        configJson = self.kwargs.get("config_json")
        intentModelId = configJson.get("config_json").get("intent_model_id")
        # TODO: inject json and have the GenericBot decipher it!!
        api = None
        log.debug("intent_model_id: %s", intentModelId)
        if intentModelId:
            api = client.connect(apicfg)
            api.set_intent_model(intentModelId)
        self.bot = generic_bot.GenericBot(
            kvStore=kvStore, configJson=configJson.get("config_json"), api=api)
        self.bot.setChannelClient(channelClient)


if __name__ == "__main__":
    # Run the command line version
    assert len(sys.argv) > 1, "usage: gbot.py /full/path/to/json_spec.json"
    d = {}
    jsonFile = sys.argv[1]
    if os.path.isfile(jsonFile):
        configJson = json.loads(open(jsonFile).read())
        d['config_json'] = configJson
    else:
        print("%s is not a valid json bot configuration file",
              jsonFile, file=sys.stderr)
    c = GenericCmdlineHandler(config_json=d)
    c.begin()


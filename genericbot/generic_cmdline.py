from __future__ import print_function
import sys, os
from os.path import expanduser, join
from flask import Flask, request, Response
from flask import Flask, current_app, jsonify, make_response
import yaml
import json
import traceback
import logging

from pymyra.api import client

from keyframe.cmdline import BotCmdLineHandler
from keyframe import channel_client
from keyframe import messages
from keyframe import config
import generic_bot
from keyframe import bot_stores

log = logging.getLogger(__name__)

# Deployment for command line
class GenericCmdlineHandler(BotCmdLineHandler):

    def getChannelClient(self, cf):
        return channel_client.getChannelClient(
            channel=messages.CHANNEL_CMDLINE,
            requestType=None,
            config=cf)

    def init(self):
        log.debug("GenericCmdlineHandler.init")
        # channel configuration
        cf = config.getConfig()
        self.channelClient = self.getChannelClient(cf)
        self.kvStore = self.kwargs.get("kvStore")
        assert self.kvStore, "kvStore is required"
        self.cfg = self.kwargs.get("cfg")
        assert self.cfg, "config is required"

        accountId = self.kwargs.get("accountId")
        accountSecret = self.kwargs.get("accountSecret")
        configJson = self.kwargs.get("config_json")
        log.debug("configJson: %s", configJson)
        bms = bot_stores.BotMetaStore(kvStore=self.kvStore)
        if not len(configJson.keys()):
            log.debug("going to get json spec")
            agentId = self.kwargs.get("agentId")
            configJson = bms.getJsonSpec(accountId, agentId)

        cj = configJson.get("config_json")
        intentModelParams = cj.get("intent_model_params")

        # TODO: inject json and have the GenericBot decipher it!!
        api = None
        log.debug("GOT intentModelParams: %s",
                  intentModelParams)
        if intentModelParams:
            apicfg = {
                "account_id": accountId,
                "account_secret": accountSecret,
                "hostname": self.cfg.MYRA_API_HOSTNAME
            }
            api = client.connect(apicfg)
            #api.set_intent_model(intentModelId)
            api.set_params(intentModelParams)
        self.bot = generic_bot.GenericBot(
            kvStore=self.kvStore, configJson=configJson.get("config_json"), api=api)
        self.bot.setChannelClient(self.channelClient)



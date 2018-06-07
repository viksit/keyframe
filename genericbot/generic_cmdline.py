from __future__ import print_function
from __future__ import absolute_import
import sys, os
from os.path import expanduser, join
from flask import Flask, request, Response
from flask import Flask, current_app, jsonify, make_response
import yaml
import json
import traceback
import logging

#from pymyra.api import client

from keyframe.cmdline import BotCmdLineHandler
from keyframe import channel_client
from keyframe import messages
from keyframe import config
from . import generic_bot
from keyframe import bot_stores

import pymyra.api.inference_proxy_client as inference_proxy_client
import pymyra.api.inference_proxy_api as inference_proxy_api

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
        #accountSecret = self.kwargs.get("accountSecret")
        configJson = self.kwargs.get("config_json")
        agentId = self.kwargs.get("agentId")

        log.debug("configJson: %s", configJson)
        bms = bot_stores.BotMetaStore(kvStore=self.kvStore)
        if not len(list(configJson.keys())):
            log.debug("going to get json spec")
            agentId = self.kwargs.get("agentId")
            configJson = bms.getJsonSpec(accountId, agentId)

        cj = configJson.get("config_json")
        intentModelParams = cj.get("intent_model_params")

        # TODO: inject json and have the GenericBot decipher it!!
        api = None
        log.debug("GOT intentModelParams: %s",
                  intentModelParams)
        #if intentModelParams:
        ipc = inference_proxy_client.InferenceProxyClient(
            host=self.cfg.MYRA_INFERENCE_PROXY_LB,
            port=self.cfg.MYRA_INFERENCE_PROXY_LB_PORT)
        api = inference_proxy_api.InferenceProxyAPI(
            inference_proxy_client=ipc)

        self.bot = generic_bot.GenericBot(
            kvStore=self.kvStore, configJson=cj, api=api, accountId=accountId, agentId=agentId)
        self.bot.setChannelClient(self.channelClient)



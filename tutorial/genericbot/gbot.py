from __future__ import print_function
import sys, os
from os.path import expanduser, join
from flask import Flask, request, Response
from flask import Flask, current_app

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
from keyframe import generic_bot_api

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
    # store_api.TYPE_LOCALFILE,
    #store_api.TYPE_DYNAMODB,
    store_api.TYPE_INMEMORY,
    config.Config())

class DB(object):

    @classmethod
    def get(cls, accountId, agentid):

        return {
            "config_json": {
            "intent_model_id": "m-msvm-cd46649818196b1b370e452a3",
            "intents":
            {"intent_23e05cd52ade452283835b0f59f70586":
             {"text": "Sure! We can do that.",
              "api_id": "",
              "intent_type":"api",
              "slots":[{"prompt":"What is your email?", "name":"email"}],
              "parse_original": False,
              "parse_response": False
             },
             "intent_5c1b3bce6d954a829240b601ea6e006c":
             {"text": "After we receive and process your gift, we will send you a tax receipt within a week.", "api_id": "", "intent_type":"api",
              "slots":[{"prompt":"What is the applicable tax year?", "name":"tax_year"},
                       {"prompt":"Which state is the tax receipt for?", "name":"tax_state"}]},
             "intent_ec8eac3d216344fab1b570effba528d0":
             {"text": "Once we receive your donation, it takes up to a week to process. By two weeks, you will receive a tax receipt and confirmation letter via mail.",
              "api_id": "", "intent_type":"api"},
             "default": {"text": "Sorry I cannot understand your question. Let me forward you to a support agent.", "intent_type":"api"}
        }
        }}


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
        if not len(configJson.keys()):
            agentId = self.kwargs.get("agentId")
            accountId = self.kwargs.get("accountId")
            configJson = DB.get(accountId, agentId)

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


# Deployment for lambda

app = Flask(__name__)


class GenericBotHTTPAPI(generic_bot_api.GenericBotAPI):

    """
    When a request comes in, we'll have to take the user_id
    and agent_id to make a query into the database.
    This retrieves a json, which is what we use to run the bot for the given
    request.

    """

    @classmethod
    def fetchBotJsonSpec(cls, **kwargs):
        """
        Given a key to db, fetch json from there
        """
        with app.app_context():
            if current_app.config["run_mode"] == "file":
                log.info("(++) Running in file mode")
                GenericBotHTTPAPI.configJson = current_app.config["config_json"]
            elif current_app.config["run_mode"] == "db":
                agentId = kwargs.get("agentId")
                accountId = kwargs.get("accountId")
                GenericBotHTTPAPI.agentId = agentId
                GenericBotHTTPAPI.accountId = accountId
                GenericBotHTTPAPI.configJson = DB.get(accountId, agentId)

    def getBot(self):
        configJson = GenericBotHTTPAPI.configJson
        print(":::::::::::::::;;;; cj: ", configJson)
        intentModelId = configJson.get("config_json").get("intent_model_id")
        api = None
        log.debug("intent_model_id: %s", intentModelId)
        if intentModelId:
            api = client.connect(apicfg)
            api.set_intent_model(intentModelId)

        self.bot = generic_bot.GenericBot(
            kvStore=kvStore, configJson=configJson.get("config_json"), api=api)
        print(":::::::::::::::", self.bot)

        return self.bot

@app.route("/run_agent", methods=["GET"])
def run_agent():
    accountId = request.args.get("account_id", None)
    agentId = request.args.get("agent_id", None)
    GenericBotHTTPAPI.fetchBotJsonSpec(
        accountId=accountId,
        agentId=agentId
    )
    # The bot should be created in the getBot() function
    # Thus we need the db call to happen before this
    event = {
        "channel": messages.CHANNEL_HTTP_REQUEST_RESPONSE,
        "request-type": request.method,
        "body": request.json
    }
    r = GenericBotHTTPAPI.requestHandler(
        event=event,
        context={})
    return Response(str(r)), 200

@app.route("/ping", methods=['GET', 'POST'])
def ping():
    print("Received ping")
    resp = json.dumps({
        "status": "OK",
    })
    return Response(resp), 200


if __name__ == "__main__":
    usage = "gbot.py [cmd/http] [file/db] [file: <path to json spec> / remote: <accountId> <agentId>]"
    assert len(sys.argv) > 2, usage

    d = {}
    cmd = sys.argv[1] # cmd/http
    runtype = sys.argv[2] # file/db

    print("cmd: ", cmd, ", runtype: ", runtype)
    jsonFile = None
    accountId = None
    agentId = None

    if runtype == "file":
        jsonFile = sys.argv[3]
        if os.path.isfile(jsonFile):
            configJson = json.loads(open(jsonFile).read())
            d['config_json'] = configJson
        else:
            print("%s is not a valid json bot configuration file" %
                  jsonFile, file=sys.stderr)
    elif runtype == "db":
        accountId = sys.argv[3]
        agentId = sys.argv[4]

    if cmd == "cmd":
        c = GenericCmdlineHandler(config_json=d, accountId=accountId, agentId=agentId)
        c.begin()

    elif cmd == "http":
        app.config["run_mode"] = runtype
        app.config["config_json"] = d
        app.run(debug=True)

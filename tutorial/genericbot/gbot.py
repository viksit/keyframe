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
    store_api.TYPE_LOCALFILE,
    #store_api.TYPE_DYNAMODB,
    #store_api.TYPE_INMEMORY,
    config.Config())


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


# Deployment for lambda

app = Flask(__name__)

class GenericBotHTTPAPI(generic_bot_api.GenericBotAPI):

    """
    When a request comes in, we'll have to take the user_id
    and agent_id to make a query into the database.
    This retrieves a json, which is what we use to run the bot for the given
    request.

    """
    def getBotJsonSpecFromFile(self):
        res = None
        # See if app.config has it
        with app.app_context():
            # within this block, current_app points to app.
            if "config_json" in current_app.config:
                res = current_app.config["config_json"]
        return res

    def getBot(self):
        configJson = None
        runMode = None

        with app.app_context():
            if "run_mode" in current_app.config:
                runMode = current_app.config["run_mode"]
                configJson = self.getBotJsonSpecFromFile()

        if not runMode:
            # Fetch config from a remote server
            configJson = self.getBotJsonSpecFromDB()

        intentModelId = configJson.get("config_json").get("intent_model_id")
        api = None
        log.debug("intent_model_id: %s", intentModelId)
        if intentModelId:
            api = client.connect(apicfg)
            api.set_intent_model(intentModelId)
        self.bot = generic_bot.GenericBot(
            kvStore=kvStore, configJson=configJson.get("config_json"), api=api)
        return self.bot

@app.route("/run_agent", methods=["GET"])
def localapi():
    user_id = request.args.get("user_id", None)
    agent_id = request.args.get("agent_id", None)
    event = {
        "agent_id": agent_id,
        "user_id": user_id,
        "channel": messages.CHANNEL_HTTP_REQUEST_RESPONSE,
        "request-type": request.method,
        "body": request.json
    }
    r = GenericBotHTTPAPI.requestHandler(
        event=event,
        context={})
    return Response(str(r)), 200

@app.route('/ping', methods=['GET', 'POST'])
def ping():
    print("Received ping")
    resp = json.dumps({
        "status": "OK",
        "request": request.data
    })
    return Response(resp), 200


if __name__ == "__main__":
    # Run the command line version
    assert len(sys.argv) > 1, "usage: gbot.py [cmd/http] /full/path/to/json_spec.json"

    d = {}
    cmd = sys.argv[1]
    jsonFile = sys.argv[2]

    if os.path.isfile(jsonFile):
        configJson = json.loads(open(jsonFile).read())
        d['config_json'] = configJson
    else:
        print("%s is not a valid json bot configuration file",
              jsonFile, file=sys.stderr)

    if cmd == "cmd":
        c = GenericCmdlineHandler(config_json=d)
        c.begin()

    elif cmd == "http":
        app.config["run_mode"] = "local"
        app.config["config_json"] = d
        app.run(debug=True)

from __future__ import print_function
import sys, os
from os.path import expanduser, join
from flask import Flask, request, Response
from flask import Flask, current_app, jsonify, make_response
import yaml
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

log = logging.getLogger(__name__)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
logformat = "[%(levelname)1.1s %(asctime)s %(name)s] %(message)s"
formatter = logging.Formatter(logformat)
ch.setFormatter(formatter)
log.addHandler(ch)
log.setLevel(logging.DEBUG)
log.propagate = False

REALM = "dev"

# TODO:
# Initialize via a configuration file
kvStore = store_api.get_kv_store(
    # store_api.TYPE_LOCALFILE,
    store_api.TYPE_DYNAMODB,
    # store_api.TYPE_INMEMORY,
    config.Config())



"""
BotMetaStore
{
  "botmeta.<acctid>.<agentid>" : {
     "jsonSpec": {},
   }
}
"""

class BotMetaStore(object):

    def __init__(self, kvStore):
        self.kvStore = kvStore

    def _botMetaKey(self, accountId, agentId):
        k = "botmeta.%s.%s" % (accountId, agentId)
        return k

    def getJsonSpec(self, accountId, agentId):
        """
        Should return a python dict
        """
        k = self._botMetaKey(accountId, agentId)
        return json.loads(self.kvStore.get_json(k))

    def putJsonSpec(self, accountId, agentId, jsonSpec):
        """
        Input is a python dict, and stores it as json
        """
        k = self._botMetaKey(accountId, agentId)
        self.kvStore.put_json(k, json.dumps(jsonSpec))

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
        bms = BotMetaStore(kvStore=kvStore)
        if not len(configJson.keys()):
            agentId = self.kwargs.get("agentId")
            accountId = self.kwargs.get("accountId")
            accountSecret = self.kwargs.get("accountSecret")
            configJson = bms.getJsonSpec(accountId, agentId)

        intentModelId = configJson.get("config_json").get("intent_model_id")
        # TODO: inject json and have the GenericBot decipher it!!
        api = None
        log.debug("intent_model_id: %s", intentModelId)
        if intentModelId:
            apicfg = {
                "account_id": accountId,
                "account_secret": accountSecret,
                "hostname": "api.%s.myralabs.com" % (REALM)
            }
            api = client.connect(apicfg)
            api.set_intent_model(intentModelId)
        self.bot = generic_bot.GenericBot(
            kvStore=kvStore, configJson=configJson.get("config_json"), api=api)
        self.bot.setChannelClient(channelClient)


# Deployment for lambda

app = Flask(__name__)
app.config['DEBUG'] = True

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
        bms = BotMetaStore(kvStore)
        with app.app_context():

            if "run_mode" in current_app.config and \
               current_app.config["run_mode"] == "file":
                log.info("(++) Running in file mode")
                GenericBotHTTPAPI.configJson = current_app.config["config_json"]

            # We're in Flask deployment mode (run_mode is "DB")
            else:
                log.info("Running in flask deployment mode")
                agentId = kwargs.get("agentId")
                accountId = kwargs.get("accountId")
                accountSecret = kwargs.get("accountSecret")

                GenericBotHTTPAPI.agentId = agentId
                GenericBotHTTPAPI.accountId = accountId
                GenericBotHTTPAPI.accountSecret = accountSecret
                GenericBotHTTPAPI.configJson = bms.getJsonSpec(accountId, agentId)
                log.info("(::) json config spec: %s", GenericBotHTTPAPI.configJson)

    def getBot(self):
        accountId = GenericBotHTTPAPI.accountId
        accountSecret = GenericBotHTTPAPI.accountSecret
        agentId = GenericBotHTTPAPI.agentId
        configJson = GenericBotHTTPAPI.configJson
        log.info("(::) agentId: %s, accountId: %s", agentId, accountId)

        intentModelId = configJson.get("config_json").get("intent_model_id")
        api = None
        log.debug("intent_model_id: %s", intentModelId)
        if intentModelId:
            apicfg = {
                "account_id": accountId,
                "account_secret": accountSecret,
                "hostname": "api.%s.myralabs.com" % (REALM)
            }
            api = client.connect(apicfg)
            api.set_intent_model(intentModelId)

        self.bot = generic_bot.GenericBot(
            kvStore=kvStore,
            configJson=configJson.get("config_json"),
            api=api,
            accountId=accountId,
            agentId=agentId)
        return self.bot

@app.route("/run_agent", methods=["GET", "POST"])
def run_agent():
    accountId = request.args.get("account_id", None)
    accountSecret = request.args.get("account_secret", None)
    agentId = request.args.get("agent_id", None)
    GenericBotHTTPAPI.fetchBotJsonSpec(
        accountId=accountId,
        agentId=agentId,
        accountSecret=accountSecret
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
    return jsonify(r)



# Slack

class Message(object):
    """
    Instanciates a Message object to create and manage
    Slack onboarding messages.
    """
    def __init__(self):
        super(Message, self).__init__()
        self.channel = ""
        self.timestamp = ""
        self.text = ("Welcome to Slack! We're so glad you're here. "
                     "\nGet started by completing the steps below.")
        self.emoji_attachment = {}
        self.pin_attachment = {}
        self.share_attachment = {}
        self.attachments = [self.emoji_attachment,
                            self.pin_attachment,
                            self.share_attachment]

    def create_attachments(self):
        """
        Open JSON message attachments file and create attachments for
        onboarding message. Saves a dictionary of formatted attachments on
        the bot object.
        """
        with open('welcome.json') as json_file:
            json_dict = yaml.safe_load(json_file)
            json_attachments = json_dict["attachments"]
            [self.attachments[i].update(json_attachments[i]) for i
             in range(len(json_attachments))]


# Mapping of team -> {teamid, bottoken}
# We'll map accountId and secret/agent to the team id/bot token in dynamodb
# 3oPxV9oFXxzHYxuvpy56a9 c504f1c49182b50abb14ee4cb2a75e83bfe81149 70aab44c87e84dd1843c8f15436616e1
botmetalocal = {
    "T06SXL7GV": {
        "team_id": "T06SXL7GV",
        "bot_token": "xoxb-121415322561-hkR3eLghiCpVlgMZ5DrxExNh",
        "concierge_meta": {
            "account_id": "3oPxV9oFXxzHYxuvpy56a9",
            "account_secret": "c504f1c49182b50abb14ee4cb2a75e83bfe81149",
            "agent_id": "70aab44c87e84dd1843c8f15436616e1"
        }
    }
}

# TODO(viksit): rename this to something better.
@app.route("/listening", methods=["GET", "POST"])
def run_agent_slack():
    print("gello")
    # TODO(viksit): see notes for refactor
    slackEvent = request.json
    print(slackEvent)
    if "event" not in slackEvent:
        return make_response("[NO EVENT IN SLACK REQUEST]", 404, {"X-Slack-No-Retry": 1})

    event = slackEvent["event"]
    # ignore bot message notification
    if "subtype" in event:
        if event["subtype"] == "bot_message":
            message = "Ignoring the bot message notification"
            # Return a helpful error message
            return make_response(message, 200, {"X-Slack-No-Retry": 1})

    eventType = slackEvent["event"]["type"]
    if eventType != "message":
        return make_response("Ignore event that is not of type 'message'", 200, {"X-Slack-No-Retry": 1})

    messageText = slackEvent.get("event", {}).get("text", None)
    if not messageText:
        return make_response("[NO MESSAGE IN SLACK REQUEST]",
                             404,
                             {"X-Slack-No-Retry": 1})

    # Process this message from slack
    userId = slackEvent["event"].get("user")
    teamId = slackEvent["team_id"]
    botToken = None

    if teamId in botmetalocal:
        botToken = botmetalocal.get(teamId).get("bot_token")

    assert botToken is not None, "This team is not registered with Concierge"

    # Myra concierge information
    conciergeMeta = botmetalocal.get(teamId).get("concierge_meta")
    accountId = conciergeMeta.get("account_id")
    accountSecret = conciergeMeta.get("account_secret")
    agentId = conciergeMeta.get("agent_id")

    GenericBotHTTPAPI.fetchBotJsonSpec(
        accountId=accountId,
        agentId=agentId,
        accountSecret=accountSecret
    )

    # The bot should be created in the getBot() function
    # Thus we need the db call to happen before this

    event = {
        "channel": messages.CHANNEL_SLACK,
        "request-type": request.method,
        "body": request.json,
        "channel-meta": {
            "user_id": userId,
            "team_id": teamId,
            "bot_token": botToken
        }
    }
    r = GenericBotHTTPAPI.requestHandler(
        event=event,
        context={})
    print(r)
    return make_response("NOOP", 200, {"X-Slack-No-Retry": 1})

# End slack code

@app.route("/ping", methods=['GET', 'POST'])
def ping():
    print("Received ping")
    resp = json.dumps({
        "status": "OK",
    })
    return Response(resp), 200


if __name__ == "__main__":
    usage = "gbot.py [cmd/http] [file/db] [file: <path to json spec> / remote: <accountId> <accountSecret> <agentId>]"
    assert len(sys.argv) > 2, usage

    d = {}
    cmd = sys.argv[1] # cmd/http
    runtype = sys.argv[2] # file/db

    print("(++) cmd: ", cmd, ", runtype: ", runtype)
    jsonFile = None
    accountId = None
    agentId = None
    accountSecret = None

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
        accountSecret = sys.argv[4]
        agentId = sys.argv[5]

    if cmd == "cmd":
        c = GenericCmdlineHandler(config_json=d, accountId=accountId, accountSecret = accountSecret, agentId=agentId)
        c.begin()

    elif cmd == "http":
        app.config["run_mode"] = runtype
        app.config["config_json"] = d
        app.run(debug=True)

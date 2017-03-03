from __future__ import print_function
import sys, os
from os.path import expanduser, join
from flask import Flask, request, Response
from flask import Flask, current_app, jsonify, make_response
from functools import wraps
import yaml
import json
import traceback
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
import generic_bot
import generic_bot_api
import generic_cmdline
import keyframe.bot_stores as bot_stores

#log = logging.getLogger(__name__)
# Make the logger used by keyframe, but not the root logger.
log = logging.getLogger("keyframe")
# ch = logging.StreamHandler(sys.stdout)
# ch.setLevel(logging.DEBUG)
# logformat = "[%(levelname)1.1s %(asctime)s %(name)s] %(message)s"
# formatter = logging.Formatter(logformat)
# ch.setFormatter(formatter)
# log.addHandler(ch)
# LOG_LEVEL = int(os.getenv("LOG_LEVEL", 10))
# log.setLevel(LOG_LEVEL)
# log.propagate = False

# log2 = logging.getLogger("pymyra")
# log2.addHandler(ch)
# log2.setLevel(LOG_LEVEL)

# TODO:
# Initialize via a configuration file
kvStore = store_api.get_kv_store(
    # store_api.TYPE_LOCALFILE,
    store_api.TYPE_DYNAMODB,
    # store_api.TYPE_INMEMORY,
    config.getConfig())

# Deployment for lambda

def wrap_exceptions(func):
    """Make sure exceptions are logged.
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log.exception("GOT EXCEPTION")
            r = Response(response=str(e), status=500)
            return r
    return decorated_function

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
        bms = bot_stores.BotMetaStore(kvStore)
        with app.app_context():

            if "run_mode" in current_app.config and \
               current_app.config["run_mode"] == "file":
                log.info("(++) Running in file mode")
                GenericBotHTTPAPI.configJson = current_app.config

            # We're in Flask deployment mode (run_mode is "DB")
            else:
                log.info("Running in flask deployment mode")
                agentId = kwargs.get("agentId")
                accountId = kwargs.get("accountId")
                accountSecret = kwargs.get("accountSecret")

                GenericBotHTTPAPI.agentId = agentId
                GenericBotHTTPAPI.accountId = accountId
                GenericBotHTTPAPI.accountSecret = accountSecret
                js = bms.getJsonSpec(accountId, agentId)
                GenericBotHTTPAPI.configJson = js
                #log.debug("(::) json config spec: %s", GenericBotHTTPAPI.configJson)
                if not js:
                    raise Exception("Json spec not found for %s", kwargs)

    def getBot(self):
        accountId = GenericBotHTTPAPI.accountId
        accountSecret = GenericBotHTTPAPI.accountSecret
        agentId = GenericBotHTTPAPI.agentId
        configJson = GenericBotHTTPAPI.configJson
        log.info("(::) agentId: %s, accountId: %s", agentId, accountId)

        intentModelId = configJson.get("config_json").get("intent_model_id")
        modelParams = configJson.get("config_json").get("params")

        api = None
        log.debug("intent_model_id: %s, modelParams: %s",
                  intentModelId, modelParams)
        if intentModelId:
            apicfg = {
                "account_id": accountId,
                "account_secret": accountSecret,
                "hostname": cfg.MYRA_API_HOSTNAME
            }
            api = client.connect(apicfg)
            api.set_intent_model(intentModelId)
            api.set_params(modelParams)

        self.bot = generic_bot.GenericBot(
            kvStore=kvStore,
            configJson=configJson.get("config_json"),
            api=api,
            accountId=accountId,
            agentId=agentId)
        return self.bot

@app.route("/run_agent", methods=["GET", "POST"])
@wrap_exceptions
def run_agent():
    accountId = request.args.get("account_id", None)
    accountSecret = request.args.get("account_secret", None)
    agentId = request.args.get("agent_id", None)
    GenericBotHTTPAPI.fetchBotJsonSpec(
        accountId=accountId,
        agentId=agentId,
        accountSecret=accountSecret
    )
    rid = request.args.get("rid", None)
    # The bot should be created in the getBot() function
    # Thus we need the db call to happen before this
    event = {
        "channel": messages.CHANNEL_HTTP_REQUEST_RESPONSE,
        "request-type": request.method,
        "body": request.json,
        "rid": rid
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
# botmetalocal = {
#     "slack.T06SXL7GV": {
#         "team_id": "T06SXL7GV",
#         "bot_token": "xoxb-121415322561-hkR3eLghiCpVlgMZ5DrxExNh",
#         "concierge_meta": {
#             "account_id": "BIRsNx4aBt9nNG6TmXudl",
#             "account_secret": "f947dee60657b7df99cceaecc80dd4d644a5e3bd",
#             "agent_id": "a7e4b5d749c74a8bb15e35a12a1bc5c6"
#         }
#     },
#     # "T06SXL7GV": {
#     #     "team_id": "T06SXL7GV",
#     #     "bot_token": "xoxb-121415322561-hkR3eLghiCpVlgMZ5DrxExNh",
#     #     "concierge_meta": {
#     #         "account_id": "3oPxV9oFXxzHYxuvpy56a9",
#     #         "account_secret": "c504f1c49182b50abb14ee4cb2a75e83bfe81149",
#     #         "agent_id": "70aab44c87e84dd1843c8f15436616e1"
#     #     }
#     # }
# }
ads = bot_stores.AgentDeploymentStore(kvStore=kvStore)
cfg = config.getConfig()

# By default get dev settings.
SLACK_BOT_ID = cfg.SLACK_BOT_ID
slack_bot_msg_ref = "<@%s>" % (SLACK_BOT_ID,)
SLACK_VERIFICATION_TOKEN = cfg.SLACK_VERIFICATION_TOKEN

# TODO(viksit): rename this to something better.
@app.route("/listening", methods=["GET", "POST"])
def run_agent_slack():
    log.info("/listening %s", request.url)
    # Always make a response. If response is not going to be 200,
    # then add the no-retry header so slack doesn't keep trying.
    try:
        return _run_agent_slack()
    except:
        traceback.print_exc()
        return make_response("Unexpected Error!", 500, {"X-Slack-No-Retry": 1})

def _run_agent_slack():
    # TODO(viksit): see notes for refactor
    slackEvent = request.json
    if not slackEvent:
        return make_response("invalid payload", 400, {"X-Slack-No-Retry": 1})

    log.debug("request.json: %s", slackEvent)
    if "challenge" in slackEvent:
        return make_response(slackEvent["challenge"], 200, {
            "content_type": "application/json"
        })

    if SLACK_VERIFICATION_TOKEN != slackEvent.get("token"):
        log.warn("Invalid slack verification token: %s", slackEvent.get("token"))
        # By adding "X-Slack-No-Retry" : 1 to our response headers, we turn off
        # Slack's automatic retries during development.
        return make_response("Invalid verification token", 403, {"X-Slack-No-Retry": 1})

    if "event" not in slackEvent:
        return make_response("[NO EVENT IN SLACK REQUEST]", 404, {"X-Slack-No-Retry": 1})

    event = slackEvent["event"]
    # ignore bot message notification
    if "subtype" in event:
        if event["subtype"] == "bot_message":
            log.debug("ignoring event with subtype: bot_message")
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

    # We only want to process direct messages or messages addressed to this
    # bot in a channel.
    channel = event.get("channel")
    processMsg = channel.startswith("D")  # This may mean direct msg - use for now.
    msg = event.get("text", "")
    hasBotId = msg.find(slack_bot_msg_ref)
    log.debug("hasBotId: %s", hasBotId)
    processMsg |= (channel.startswith("C") and hasBotId > -1)
    log.debug("processMsg: %s", processMsg)
    if not processMsg:
        return make_response("Ignore event - not DM or addressed to bot", 200, {"X-Slack-No-Retry": 1})

    # Process this message from slack
    userId = slackEvent["event"].get("user")
    teamId = slackEvent["team_id"]
    msgChannel = event["channel"]
    botToken = None

    #botToken = botmetalocal.get("slack." + str(teamId)).get("bot_token")
    agentDeploymentMeta = ads.getJsonSpec(teamId, "slack")
    botToken = agentDeploymentMeta.get("bot_token")

    if not botToken:
        raise Exception("This team is not registered with Concierge")

    # Myra concierge information
    conciergeMeta = agentDeploymentMeta.get("concierge_meta")
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
            "bot_token": botToken,
            "msg_channel": msgChannel
        }
    }
    r = GenericBotHTTPAPI.requestHandler(
        event=event,
        context={})
    log.debug("going to return a 200 status after request is handled")
    return make_response("NOOP", 200, {"X-Slack-No-Retry": 1})

# End slack code

# TODO: Remove this 
@app.route("/anxoivch8wxoiu8dvhwnwo93", methods=['GET', 'POST'])
def debug_obfuscated():
    log.info(request.url)
    resp = json.dumps({
        "SLACK_BOT_ID":SLACK_BOT_ID,
        "SLACK_VERIFICATION_TOKEN":SLACK_VERIFICATION_TOKEN,
        "env.STAGE":os.environ.get("STAGE")
    })
    return Response(resp), 200

@app.route("/ping", methods=['GET', 'POST'])
def ping():
    print("Received ping")
    resp = json.dumps({
        "status": "OK",
        "env.STAGE":os.environ.get("STAGE")
    })
    return Response(resp), 200


if __name__ == "__main__":
    usage = "gbot.py [cmd/http] [file/db] [file: <accountId> <accountSecret> <path to json spec> / db: <accountId> <accountSecret> <agentId>]"
    assert len(sys.argv) > 2, usage

    logging.basicConfig()
    log.setLevel(int(os.getenv("KEYFRAME_LOGLEVEL", 20)))
    log.debug("debug log")
    log.info("info log")

    d = {}
    cmd = sys.argv[1] # cmd/http
    runtype = sys.argv[2] # file/db

    log.info("(++) cmd: %s, runtime: %s", cmd, runtype)
    jsonFile = None
    agentId = None

    accountId = sys.argv[3]
    accountSecret = sys.argv[4]

    if runtype == "file":
        jsonFile = sys.argv[5]
        if os.path.isfile(jsonFile):
            configJson = json.loads(open(jsonFile).read())
            #d['config_json'] = configJson
            d = configJson
        else:
            print("%s is not a valid json bot configuration file" %
                  jsonFile, file=sys.stderr)
            sys.exit(1)
        log.info("config_json: %s", d['config_json'])
    elif runtype == "db":
        agentId = sys.argv[5]

    if cmd == "cmd":
        c = generic_cmdline.GenericCmdlineHandler(config_json=d, accountId=accountId, accountSecret = accountSecret, agentId=agentId, kvStore=kvStore, cfg=cfg)
        c.begin()

    elif cmd == "script":
        scriptFile = sys.argv[6]
        c = generic_cmdline.ScriptHandler(config_json=d, accountId=accountId, accountSecret = accountSecret, agentId=agentId, kvStore=kvStore, cfg=cfg)
        c.scriptFile(scriptFile=scriptFile)
        num_errors = c.executeScript()
        if num_errors > 0:
            log.error("num_errors: %s", num_errors)
            sys.exit(1)

    elif cmd == "http":
        app.config["run_mode"] = runtype
        app.config["config_json"] = d
        app.run(debug=True)

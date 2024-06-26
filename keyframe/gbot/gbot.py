#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import

import sys, os
import time

print("[%s] STARTING GBOT" % (time.time(),), file=sys.stderr)
print("PYTHONPATH: %s" % (sys.path,), file=sys.stderr)

from os.path import expanduser, join
from flask import Flask, request, Response, send_from_directory
from flask import Flask, current_app, jsonify, make_response
from flask_cors import CORS, cross_origin
import datetime
import urllib

print("[%s] STEP 10" % (time.time(),), file=sys.stderr)

import boto
import mimetypes

from functools import wraps
import yaml
import json
import traceback
import base64
import logging
from six.moves import range

print("[%s] STEP 20" % (time.time(),), file=sys.stderr)

import keyframe.logservice
log = logging.getLogger("keyframe.gbot.gbot")

print("[%s] STEP 30" % (time.time(),), file=sys.stderr)

#from pymyra.api import client
import pymyra.api.inference_proxy_client as inference_proxy_client
import pymyra.api.inference_proxy_api as inference_proxy_api

print("[%s] STEP 32" % (time.time(),), file=sys.stderr)

from keyframe.cmdline import BotCmdLineHandler
from keyframe.base import BaseBot
from keyframe.actions import ActionObject
from keyframe.slot_fill import Slot
from keyframe.bot_api import BotAPI
from keyframe import channel_client
from keyframe import intercom_messenger

print("[%s] STEP 35" % (time.time(),), file=sys.stderr)

from keyframe import messages
from keyframe import config
from keyframe import store_api
from keyframe import bot_stores
import keyframe.event_api as event_api
import keyframe.utils
import keyframe.widget_target

print("[%s] STEP 38" % (time.time(),), file=sys.stderr)

from keyframe.genericbot import generic_bot
from keyframe.genericbot import generic_bot_api
from keyframe.genericbot import generic_cmdline

#import keyframe.intercom_messenger as im_utils
from keyframe import imlib
from keyframe.intercom_messenger import _pprint


#app = Flask(__name__)
#CORS(app, supports_credentials=True)

#app.config['DEBUG'] = True
#app.config['DEBUG'] = False

#VERSION = "3.0.2"
VERSION = keyframe.utils.getFromFileOrDefault(
    "keyframe_version.txt", "default")

print("[%s] STEP 40" % (time.time(),), file=sys.stderr)

cfg = config.getConfig()
_kvStore = None
def getKVStore():
    global _kvStore
    if not _kvStore:
        _kvStore = store_api.get_kv_store(
            # store_api.TYPE_LOCALFILE,
            os.getenv("KEYFRAME_KV_STORE_TYPE", store_api.TYPE_DYNAMODB),
            # store_api.TYPE_INMEMORY,
            cfg)
    return _kvStore

# cachedKvStore = kvStore
# KVSTORE_CACHE_SECONDS = int(os.getenv("KVSTORE_CACHE_SECONDS", 0))
# if KVSTORE_CACHE_SECONDS:
#     cachedKvStore = store_api.MemoryCacheKVStore(
#         kvStore=kvStore, cacheExpirySeconds=KVSTORE_CACHE_SECONDS)
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
            r = Response(response="%s"%(e,), status=500)
            return r
    return decorated_function

app = Flask(__name__, static_folder='static')
CORS(app, supports_credentials=True)

app.config['DEBUG'] = True

print("[%s] STEP 50" % (time.time(),), file=sys.stderr)

class SpecException(Exception):
    # SpecException should just have one mandatory argument.
    def __init__(self, msg):
        super(SpecException, self).__init__(msg)


@app.route('/specs', methods=['GET'])
def specs():
    specName = request.args.get("specname")
    if not specName:
        return Response(
            "Specify specname and other required parameters for specname")
    try:
        if specName == "botspec":
            spec = _botspec()
            return jsonify(spec)
        if specName == "widgettargetconfig":
            spec = _widgettargetconfig()
            return jsonify(spec)
        if specName == "intercomAgentDeploymentMeta":
            appId = request.args.get("appId")
            if not appId:
                return Response("must provide appId")
            agentDeploymentMeta = getIntercomAgentDeploymentMeta(appId)
            return jsonify(agentDeploymentMeta)
        return Response("unknown specname: %s" % (specName,))
    except SpecException as se:
        return Response(se.args[0])


def _widgettargetconfig():
    kvStore = getKVStore()
    agentId = request.args.get("agent_id")
    if not agentId:
        raise SpecException("agent_id is required")
    wtc = keyframe.widget_target.getWidgetTargetConfig(
                kvStore, agentId)
    return wtc

def _botspec():
    accountId = request.args.get("account_id")
    agentId = request.args.get("agent_id")
    if not (accountId and agentId):
        raise SpecException("agent_id and account_id required")
    try:
        GenericBotHTTPAPI.fetchBotJsonSpec(accountId=accountId, agentId=agentId)
        return GenericBotHTTPAPI.configJson
    except:
        raise SpecException(
            "Could not find botspec for account_id: %s and agent_id: %s" % (
                accountId, agentId))


@app.route('/healthcheck')
def healthcheck():
    print("healthcheck called")
    h = os.getenv("HEALTHCHECK_RESPONSE", "ok")
    return Response(h), 200

@app.route('/appdebug')
def app_debug():
    print_request_details()
    action = request.args.get("action")
    if action == "get_headers":
        return jsonify(dict(request.headers))
    r = {"myregionid":os.getenv("REGION_ID")}
    return jsonify(r)

publicUploadConn = None
def getPublicUploadConn():
    global publicUploadConn
    publicUploadConn = boto.s3.connect_to_region(
        cfg.AWS_S3_REGION,
        aws_access_key_id=cfg.AWS_S3_PUBLIC_UPLOAD_ACCESS_KEY_ID,
        aws_secret_access_key=cfg.AWS_S3_PUBLIC_UPLOAD_SECRET_ACCESS_KEY
    )
    return publicUploadConn

@app.route("/api/internal/sign_s3_upload", methods = ["GET"])
@cross_origin(supports_credentials=True)
@wrap_exceptions
def sign_s3_upload():
    bucketName = cfg.AWS_S3_PUBLIC_UPLOAD_BUCKET
    objectName = request.args.get("objectName")
    contentType = mimetypes.guess_type(objectName)[0]
    signedUrl = getPublicUploadConn().generate_url(
        300,
        "PUT",
        bucketName,
        objectName,
        headers = {"Content-Type": contentType, "x-amz-acl":"public-read"}
    )
    return jsonify({"signedUrl": signedUrl})

@app.route('/logtest')
def log_test():
    log.info("This is an info log")
    logging.info("logging info")
    logging.warn("logging warn")
    log.info("this is a repeating sentence. "*100)
    return Response(), 200

@app.route('/robots.txt')
def static_from_root():
    log.info("REQUEST /robots.txt")
    return send_from_directory(app.static_folder, request.path[1:])

@app.route('/widget_page_welcome', methods=["GET", "POST"])
def widget_page_welcome():
    log.info("REQUEST /widget_page (%s, %s)", request.method, request.url)
    #_pprint(request.json)
    widgetPage = intercom_messenger.WIDGET_WEBPAGE.strip()
    #widgetPage = open("%s/conf_widget_page.html" % (app.static_folder,)).read()
    appId = request.args.get("app_id")
    if not appId:
        return Response("Could not get app_id"), 500
    agentDeploymentMeta = getIntercomAgentDeploymentMeta(appId)
    d = agentDeploymentMeta.get("concierge_meta")
    if "widget_version" not in d:
        d["widget_version"] = "v3"
    d["realm"] = cfg.REALM
    widgetPage = widgetPage % d
    return widgetPage

@app.route('/widget_page', methods=["GET", "POST"])
def widget_page():
    log.info("REQUEST /widget_page (%s, %s)", request.method, request.url)
    appId = request.args.get("app_id")
    if not appId:
        return Response("Could not get app_id"), 500
    configJson = _fetchAgentJsonSpec(appId)
    if not configJson:
        raise Exception("could not find agent for appid %s" % (appId,))
    pinConfig = configJson.get("config_json", {}).get("params", {}).get("pin_json", [])
    log.info("pinConfig: %s", pinConfig)
    #print_request_details()
    #print("REQUEST.JSON: %s" % (request.json,))
    intercomDataStr = request.form.get('intercom_data')
    #print("request.form.intercom_data: %s", intercomDataStr)
    widget_webpage = None
    userQuestion = None
    if intercomDataStr:
        intercomData = json.loads(intercomDataStr)
        log.info("Got intercomData (%s): %s", type(intercomData), intercomData)
        userQuestion = intercom_messenger.getInputFromAppRequestForWidgetPage(
            appResponse=intercomData, pinConfig=pinConfig)
        #userQuestion =  intercom_messenger.getInputFromAppRequestSingleText(
        #    appResponse=intercomData, textInputId="user_question")
    if not userQuestion:
        widget_webpage = intercom_messenger.WIDGET_WEBPAGE_WELCOME
    else:
        widget_webpage = intercom_messenger.WIDGET_WEBPAGE_SEARCH

    widgetPage = widget_webpage.strip()
    agentDeploymentMeta = getIntercomAgentDeploymentMeta(appId)
    d = agentDeploymentMeta.get("concierge_meta")
    if "widget_version" not in d:
        d["widget_version"] = "v3"
    # Set INTERCOM_WIDGET_REALM to local to test with local keyframe.
    d["realm"] = cfg.REALM
    d["keyframe_realm"] = os.getenv("INTERCOM_WIDGET_REALM", cfg.REALM)
    d["title"] = _getValueFromAgentUserMessages(
        "intercomMessengerAppTitle", configJson, "Myra Help Desk")
    if userQuestion:
        d["user_question"] = userQuestion
    widgetPage = widgetPage % d
    log.info("WIDGET PAGE:")
    print(widgetPage)
    return widgetPage

# For local testing in case of some problem with /widget_page
@app.route('/widget_page_local', methods=["GET", "POST"])
def widget_page_local():
    log.info("REQUEST /widget_page_local (%s, %s)", request.method, request.url)
    _pprint(request.json)
    return send_from_directory(app.static_folder, "widget_page.html")

@app.route("/version", methods=["GET"])
def version():
    return VERSION

@app.route("/widget_target", methods=["GET"])
@cross_origin(supports_credentials=True)
def widget_target():
    log.info("widget_target invoked")
    agentId = request.args.get("agent_id")
    if not agentId:
        log.error("No agent_id given.")
        return Response(response="Invalid request.", status=400)
    log.info("agentId: %s", agentId)
    url = request.args.get("url")
    log.info("url: %s", url)
    kvStore = getKVStore()
    widgetTargetConfig = keyframe.widget_target.getWidgetTargetConfig(
        kvStore, agentId)
    #log.info("widgetTargetConfig: %s", widgetTargetConfig)
    r = keyframe.widget_target.evaluateWidgetTarget(widgetTargetConfig, url)
    if not r:
        return jsonify({
            "show_cta": False,
            "context_api_response": {
                "enabled": False,
                "contexts": []
            }
        })
    # Work out contexts
    contextConfig = keyframe.widget_target.getContextConfig(
        widgetTargetConfig, url)
    return jsonify({
        "show_cta": True,
        "context_api_response": contextConfig
    })


@app.route("/agent_pin_config", methods=["GET","POST"])
@wrap_exceptions
def agent_pin_config():
    if request.method == 'POST':
        accountId = request.json.get("account_id", None)
        agentId = request.json.get("agent_id", None)
    else:
        accountId = request.args.get("account_id", None)
        agentId = request.args.get("agent_id", None)
    log.info("agent_pin_config(account_id=%s, agent_id=%s)",
             accountId, agentId)
    GenericBotHTTPAPI.fetchBotJsonSpec(
        accountId=accountId,
        agentId=agentId)
    jsonSpec = GenericBotHTTPAPI.configJson.get("config_json")
    pinConfig = jsonSpec.get("params", {}).get("pin_json", [])
    log.info("agent_pin_config returning: %s" % (pinConfig,))
    return jsonify({
        "pinconfig": pinConfig
    })


@app.route("/agent_event", methods=["POST"])
@wrap_exceptions
def agent_event():
    r, text = _run_agent(request_api="agent_event")
    return jsonify(r)

@app.route("/event", methods=["POST"])
@wrap_exceptions
def handle_event():
    r = _handle_event()
    return jsonify(r)

def _handle_event():
    requestData = request.json
    log.info("requestData: %s", requestData)
    event_api.handleEvent(requestData, cfg)
    return {"status":"OK"}

class GenericBotHTTPAPI(generic_bot_api.GenericBotAPI):

    """
    When a request comes in, we'll have to take the user_id
    and agent_id to make a query into the database.
    This retrieves a json, which is what we use to run the bot for the given
    request.
    """
    agentId = None
    accountId = None
    #accountSecret = None

    @classmethod
    def fetchBotJsonSpec(cls, **kwargs):
        """
        Given a key to db, fetch json from there
        """
        agentId = kwargs.get("agentId")
        accountId = kwargs.get("accountId")
        #accountSecret = kwargs.get("accountSecret")
        bms = bot_stores.BotMetaStore(getKVStore())
        with app.app_context():

            if "run_mode" in current_app.config and \
               current_app.config["run_mode"] == "file":
                log.info("(++) Running in file mode")
                GenericBotHTTPAPI.configJson = current_app.config.get("config_json")
                assert GenericBotHTTPAPI.configJson

                if "cmd_mode" in current_app.config and \
                   current_app.config["cmd_mode"] == "http":
                    log.info("Running in flask deployment mode")

                    GenericBotHTTPAPI.agentId = agentId
                    GenericBotHTTPAPI.accountId = accountId
                    #GenericBotHTTPAPI.accountSecret = accountSecret

            # We're in Flask deployment mode (run_mode is "DB")
            else:
                log.info("Running in flask deployment mode")
                agentId = kwargs.get("agentId")
                accountId = kwargs.get("accountId")
                #accountSecret = kwargs.get("accountSecret")

                if not agentId:
                    # agentId could also be 'default' which is ok.
                    agentId = "default"
                js = bms.getJsonSpec(accountId, agentId)
                # In case agentId is not specified (or is 'default'), important
                # to set the actual agentId of the agent for the rest of keyframe.
                if not js:
                    raise Exception("Could not find agent spec for accountId %s, agentId %s" % (accountId, agentId))
                agentId = js.get("config_json", {}).get("agent_id")

                GenericBotHTTPAPI.agentId = agentId
                GenericBotHTTPAPI.accountId = accountId
                #GenericBotHTTPAPI.accountSecret = accountSecret
                GenericBotHTTPAPI.configJson = js
                log.debug("(::) json config spec: %s", GenericBotHTTPAPI.configJson)
                if not js:
                    raise Exception("Json spec not found for %s", kwargs)

    def getBot(self):
        accountId = GenericBotHTTPAPI.accountId
        #accountSecret = GenericBotHTTPAPI.accountSecret
        agentId = GenericBotHTTPAPI.agentId
        configJson = GenericBotHTTPAPI.configJson
        log.info("(::) agentId: %s, accountId: %s",
                 agentId, accountId)
        log.debug("configJson: %s", configJson)

        #intentModelId = configJson.get("config_json").get("intent_model_id")
        #modelParams = configJson.get("config_json").get("intent_model_params")

        api = None
        #log.debug("modelParams: %s",
        #          modelParams)
        #if modelParams:
        #    assert accountId and cfg.MYRA_INFERENCE_PROXY_LB, \
        #        "gbot has modelParams but cannot create api because no api params"
        if accountId and cfg.MYRA_INFERENCE_PROXY_LB:
            log.info("creating api")
            ipc = inference_proxy_client.InferenceProxyClient(
                host=cfg.MYRA_INFERENCE_PROXY_LB,
                port=cfg.MYRA_INFERENCE_PROXY_LB_PORT)
            api = inference_proxy_api.InferenceProxyAPI(
                inference_proxy_client=ipc)
            #api = client.connect(apicfg)
            #api.set_intent_model(intentModelId)
            #api.set_params(modelParams)

        self.bot = generic_bot.GenericBot(
            kvStore=getKVStore(),
            configJson=configJson.get("config_json"),
            api=api,
            accountId=accountId,
            agentId=agentId)
        return self.bot

@app.route("/run_agent2", methods=["POST"])
@wrap_exceptions
def run_agent2():
    #print("RUN_AGENT2 CALLED.")
    #print_request_details()
    log.info("request url: %s", request.url)
    r, text = _run_agent()
    r2 = {
        "text": text,
        "message": "Agent responded successfully",
        "result": r
    }
    resp = jsonify(r2)
    h = resp.headers

    # Seems like can't have multiple domains. Here is the browser error message:
    # The 'Access-Control-Allow-Origin' header contains multiple values 'http://localhost:8080, http://demos.myralabs.com', but only one is allowed. Origin 'http://localhost:8080' is therefore not allowed access.

    # allowOrigins = ["http://localhost:8080",
    #                "http://demos.myralabs.com"]
    # h.extend([("Access-Control-Allow-Origin", orig) for orig in allowOrigins])
    # In any case, seems like the data goes back, just the browser respects CORS.
    # But this is not a security solution.

    h['Access-Control-Allow-Origin'] = "*"
    log.info("resp.headers: %s", h)
    return resp

def _run_agent(request_api=None):
    log.info("HEADERS: %s", request.headers)
    log.info("DATA: %s", request.data)
    log.info("COOKIES: %s", request.cookies)
    requestData = None
    text = None
    accountId = None
    agentId = None
    if request.method == 'POST':
        requestData = request.json
        requestData["remote_addr"] = request.remote_addr
        text = request.json.get("text")
        accountId = request.json.get("account_id", None)
        agentId = request.json.get("agent_id", None)

    else:
        raise Exception("cannot handle this request")

    if request_api == "agent_event":
        eventType = request.json.get("event_type")
        if not eventType:
            raise Exception("Bad event. Event must have event_type.")

    GenericBotHTTPAPI.fetchBotJsonSpec(
        accountId=accountId,
        agentId=agentId
    )
    # The bot should be created in the getBot() function
    # Thus we need the db call to happen before this
    event = {
        "channel": messages.CHANNEL_HTTP_REQUEST_RESPONSE,
        "request-type": request.method,
        "body": requestData
    }
    r = GenericBotHTTPAPI.requestHandler(
        event=event,
        context={})
    return r, text


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
#ads = bot_stores.AgentDeploymentStore(kvStore=kvStore)

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
    ads = bot_stores.AgentDeploymentStore(kvStore=getKVStore())
    agentDeploymentMeta = ads.getJsonSpec(teamId, "slack")
    botToken = agentDeploymentMeta.get("bot_token")

    if not botToken:
        raise Exception("This team is not registered with Concierge")

    # Myra concierge information
    conciergeMeta = agentDeploymentMeta.get("concierge_meta")
    accountId = conciergeMeta.get("account_id")
    #accountSecret = conciergeMeta.get("account_secret")
    agentId = conciergeMeta.get("agent_id")

    GenericBotHTTPAPI.fetchBotJsonSpec(
        accountId=accountId,
        agentId=agentId
        #accountSecret=accountSecret
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

## Start intercom code
@app.route("/listener/intercom", methods=["HEAD", "GET", "POST"])
def run_agent_intercom():
    log.info("/listener/intercom: %s", request.url)
    # Always make a response. If response is not going to be 200,
    # then add the no-retry header so slack doesn't keep trying.
    if request.method == "HEAD":
        return Response(), 200

    try:
        return _run_agent_intercom()
    except:
        traceback.print_exc()
        return make_response("Unexpected Error!", 500, {"X-No-Retry": 1})

######
from intercom.client import Client
#ACCESS_TOKEN="dG9rOjY2M2NjM2FjXzM5NTVfNGMzN19iMjdjX2UzYTI5YTBhMmYwOToxOjA=" # need from intercom
#APP_ID = "iv6ijpl5" # "cp6b0zl8" for messenger
#intercom = Client(personal_access_token=ACCESS_TOKEN)

def _run_agent_intercom():
    intercomEvent = request.json
    log.info("request.args: %s", request.args)
    # TODO(nishant): how to disable intercom from sending same message multiple times
    if not intercomEvent:
        return make_response("invalid payload", 400, {"X-No-Retry": 1})

    log.info("_run_agent_intercom: request.json: %s", json.dumps(intercomEvent, indent=2))

    # Get intercom conversation ID and pass it on
    conversationId = intercomEvent.get("data").get("item").get("id")
    log.info("conversationId: %s", conversationId)
    # Myra concierge information
    # Get this from the database which stores <intercom accountid> -> <agentid map>

    #userId = "test1"
    #accountId = "3oPxV9oFXxzHYxuvpy56a9"
    #agentId = "f111cef48e1548be8d121f9649b368eb"

    #conversation = intercom.conversations.find(id=conversationId)
    #print("CONV DICT: ", conversation.__dict__)
    #print(conversation.assignee)
    #print(conversation.assignee.__dict__)

    if intercomEvent.get("topic") in ("conversation.user.created", "conversation.user.replied"):
        assignedUserEmail = intercomEvent.get("data", {}).get("item", {}).get("assignee", {}).get("email")
        assignedUserId = intercomEvent.get("data", {}).get("item", {}).get("assignee", {}).get("id")
        appId = intercomEvent.get("app_id")
        ads = bot_stores.AgentDeploymentStore(kvStore=getKVStore())
        agentDeploymentMeta = ads.getJsonSpec(appId, "intercom")
        log.info("agentDeploymentMeta: %s", agentDeploymentMeta)
        if agentDeploymentMeta:
            _config = agentDeploymentMeta.get("config", {})
            proxyUserId = None
            if _config is not None:
                proxyUserId = _config.get("intercom_proxy_agent_id")
            if assignedUserId == proxyUserId:
                log.info("This is a topic to reply to (%s)", intercomEvent.get("topic"))
                _intercom_agent_handler(agentDeploymentMeta, intercomEvent, appId)
            else:
                log.info("event for user: %s does not match proxy user: %s. dropping it.", assignedUserId, proxyUserId)
        else:
            log.info("No agent for app_id: %s. Dropping this event.", appId)

    else:
        log.info("Received event is not a target for response from this bot. Dropping it.")
    # log.debug("going to return a 200 status after request is handled")
    # return make_response("NOOP", 200, {"X-No-Retry": 1})
    res = json.dumps({})
    return Response(res), 200

## End intercom code

def _fetchAgentJsonSpec(appId):
    agentDeploymentMeta = getIntercomAgentDeploymentMeta(appId)
    if not agentDeploymentMeta:
        return None
    accountId = agentDeploymentMeta.get("concierge_meta", {}).get("account_id")
    agentId = agentDeploymentMeta.get("concierge_meta", {}).get("agent_id")
    if not (accountId or agentId):
        log.warn("Did not find required information from agentDeploymentMeta: %s", agentDeploymentMeta)
        return None

    GenericBotHTTPAPI.fetchBotJsonSpec(
        accountId=accountId,
        agentId=agentId
    )
    configJson = GenericBotHTTPAPI.configJson
    log.debug("returning json spec: %s", configJson)
    return configJson


def _intercom_msg_agent_handler(agentDeploymentMeta, intercomEvent, appId):
    log.info("agentDeploymentMeta: %s, appId: %s", agentDeploymentMeta, appId)
    accountId = agentDeploymentMeta.get("concierge_meta", {}).get("account_id")
    agentId = agentDeploymentMeta.get("concierge_meta", {}).get("agent_id")
    assert accountId and agentId, "Did not find required information from agentDeploymentMeta (%s)" % (agentDeploymentMeta,)

    GenericBotHTTPAPI.fetchBotJsonSpec(
        accountId=accountId,
        agentId=agentId
    )

    event = {
        "channel": messages.CHANNEL_INTERCOM_MSG,
        "request-type": None,
        "body": intercomEvent,
        "channel-meta": {
            "user_id": intercomEvent.get("user", {}).get("user_id"),
            "rid": None,  # seems like no rid per msg!
            "conversation_id": None,  # can't see a conv_id in the request
            "access_token": None  # This is a request/response system - no token required.
        }
    }

    r = GenericBotHTTPAPI.requestHandler(
        event=event,
        context={})
    return r

def _intercom_agent_handler(agentDeploymentMeta, intercomEvent, appId):
    log.info("agentDeploymentMeta: %s, appId: %s", agentDeploymentMeta, appId)
    accessToken = agentDeploymentMeta.get("access_token")
    accountId = agentDeploymentMeta.get("concierge_meta", {}).get("account_id")
    agentId = agentDeploymentMeta.get("concierge_meta", {}).get("agent_id")
    assert accessToken and accountId and agentId, "Did not find required information from agentDeploymentMeta (%s)" % (agentDeploymentMeta,)

    GenericBotHTTPAPI.fetchBotJsonSpec(
        accountId=accountId,
        agentId=agentId
    )

    event = {
        "channel": messages.CHANNEL_INTERCOM,
        "request-type": None,
        "body": intercomEvent,
        "channel-meta": {
            "user_id": intercomEvent.get("data", {}).get("item", {}).get("user", {}).get("user_id"),
            "rid": intercomEvent.get("id"),
            #"conversation_id": intercomEvent.get("data", {}).get("item", {}).get("conversation_message", {}).get("id"),
            "conversation_id": intercomEvent.get("data", {}).get("item", {}).get("id"),
            "access_token": accessToken,
            "proxy_admin_id": agentDeploymentMeta.get("config", {}).get("intercom_proxy_agent_id"),
            "support_admin_id": agentDeploymentMeta.get("config", {}).get("intercom_support_agent_id")
        }
    }

    r = GenericBotHTTPAPI.requestHandler(
        event=event,
        context={})

    # resBody = "This is a test response for your message at %s" % (datetime.datetime.now(),)
    # res = intercom.conversations.reply(
    #     id=conversationId,
    #     type=conversation.assignee.resource_type,
    #     admin_id=conversation.assignee.id,
    #     message_type='comment',
    #     body=resBody)

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
    log.info("Received ping")
    resp = json.dumps({
        "status": "OK",
        "env.STAGE":os.environ.get("STAGE")
    })
    return Response(resp), 200


#### ------- Intercom messenger app ----------------

def getIntercomAgentDeploymentMeta(appId):
    ads = bot_stores.AgentDeploymentStore(kvStore=getKVStore())
    agentDeploymentMeta = ads.getJsonSpec(appId, "intercom_msg")
    return agentDeploymentMeta

# This version used an intermediate map to map appid -> accountid, and then
# got the agent json. After we switched to oauth, we go directly from
# appid -> agent json because the appid is configured in the dashboard via oauth.
def getIntercomAgentDeploymentMetaUsingMap(appId, doCheck=True):
    appIdAccountIdMap = getIntercomAppIdAccountIdMap(appId)
    log.info("got appIdAccountIdMap from intercom_msg: %s", appIdAccountIdMap)
    if not appIdAccountIdMap:
        log.warn("No map for app_id %s found", appId)
        return None
    accountId = appIdAccountIdMap.get("concierge_meta", {}).get("account_id")
    accountSecret = appIdAccountIdMap.get("concierge_meta", {}).get("account_secret")

    ads = bot_stores.AgentDeploymentStore(kvStore=getKVStore())
    agentDeploymentMeta = ads.getJsonSpec(accountId, "intercom_msg")
    if doCheck:
        r = checkIntercomMsgConfigure(
            accountId=accountId, accountSecret=accountSecret,
            agentDeploymentMeta=agentDeploymentMeta)
        if r[1] != 200:
            log.warn("Check for Intercom config failed for appId %s", appId)
            return None
    return agentDeploymentMeta

def putIntercomAppIdAccountIdMap(appId, accountId, accountSecret):
    ads = bot_stores.AgentDeploymentStore(kvStore=getKVStore())
    # Below is the same format as the json for "intercom" to help transition testing.
    jsonSpec = {"concierge_meta":
                {"app_id":appId,
                 "account_id":accountId,
                 "account_secret":accountSecret}}
    ads.putJsonSpec(appId, "intercom_msg_map", jsonSpec)

def getIntercomAppIdAccountIdMap(appId):
    ads = bot_stores.AgentDeploymentStore(kvStore=getKVStore())
    appIdAccountIdMap = ads.getJsonSpec(appId, "intercom_msg_map")
    return appIdAccountIdMap

def getIntercomAgentDeploymentMetaTest(appId):
    # agent_id: "ca006972df904823925d122383b4be54" => nishant-intercom-m-20180904-1 / nishant+dev@myralabs.com
    #agentDeploymentMeta = {"connected": True, "access_token": "", "concierge_meta":{"account_id":"3rxCO9rydbBIf3DOMb9lFh", "agent_id": "ca006972df904823925d122383b4be54"}, "app_id": "cp6b0zl8"}
    # agent_id: "2b91938a2b544322b63792c4024e12ae" (wpengine_v3-dev-20181018) / demo+dev@myralabs.com
    #agentDeploymentMeta = {"connected": True, "access_token": "", "concierge_meta":{"account_id":"bd80e4cbc57f47178ef323b87fd4823d", "agent_id":"2b91938a2b544322b63792c4024e12ae"}, "app_id": "iv6ijpl5"}
    # agent_id: "3c1b9fd4341c4be09a8e8a0172cff06a" (nishant-intercom-app-search-1) / nishant+dev@myralabs.com
    agentDeploymentMeta = {"connected": True, "access_token": "",
                           "concierge_meta":{"account_id":"3rxCO9rydbBIf3DOMb9lFh",
                                             "agent_id":"3c1b9fd4341c4be09a8e8a0172cff06a"},
                           "app_id": "iv6ijpl5"}
    return agentDeploymentMeta

def checkIntercomMsgConfigure(accountId, accountSecret=None, agentDeploymentMeta=None):
    """Return tuple of string and http status code to return.
    """
    # TODO: check validity and store to AgentDeploymentStore.
    adm = agentDeploymentMeta
    if not adm:
        ads = bot_stores.AgentDeploymentStore(kvStore=getKVStore())
        adm = ads.getJsonSpec(accountId, "intercom_msg")
    if not (adm
            and adm.get("concierge_meta", {}).get("account_id") == accountId
            #and adm.get("concierge_meta", {}).get("account_secret") == accountSecret
            and True):
        log.warn("accountId: %s, accountSecret: %s. BUT adm: %s", accountId, accountSecret, adm)
        return ("Must have valid Myra account_id and account_secret and have an agent deployed for Intercom Msg", 500)
    return ("ok", 200)

# TODO: The config is checked against the effects of this api call to create a default agent for intercom_msg.
# curl -v "http://localhost:7091/api/internal/activate_agent_on_channel?agent_id=3c1b9fd4341c4be09a8e8a0172cff06a&channel=intercom_msg&user_id=3rxCO9rydbBIf3DOMb9lFh"
@app.route("/v2/intercom/configure", methods=['GET', 'POST'])
def v2_intercom_configure():
    log.info("v2_intercom_configure: %s", request.json)
    res = None
    if request.json.get("component_id") == "button_install_ok":
        # This is the install 'OK'
        res = json.dumps({"results": {"option1":"value1"}})
    elif request.json.get("component_id") == "button_install_cancel":
        return Response(), 500
    else:
        # This is the first configure call.
        appId = request.json.get("app_id")
        adm = getIntercomAgentDeploymentMeta(appId)
        log.info("IntercomAgentDeploymentMeta: %s", adm)
        if (not adm
            or not adm.get("concierge_meta", {}).get("agent_id")):
            canvas = intercom_messenger.getNoInstallCanvas()
                #msg="Make sure you have an active Myra account and a default agent.")
            res = json.dumps(canvas)
        else:
            # Configuration is complete
            res = json.dumps({"results": {"option1":"value1"}})
            # Don't send the "installokcancel" - just install it.
            #canvas = intercom_messenger.getInstallOkCancelCanvas("")
            #res = json.dumps(canvas)
            #res = json.dumps({"results": {"status":"ok"}})
    log.info("returning response: %s", res)
    return Response(res), 200


# This version asked the Intercom user for the Myra account_id and account_secret.
# Now we are using oauth to connect this user / app to the Myra account.
# This was attached to the /v2/intercom/configure route before (I think).
def v2_intercom_configure_acctid_secret_version():
    log.info("## configure ##")
    res = None
    _pprint(request.json)
    if (request.json.get("input_values")):
        log.info("here", request.json.get("input_values"))
        # This is the second configure call
        # Send back a result to deploy this application
        appId = request.json.get("app_id")
        assert appId, "Nothing can happen without app_id"
        iv = request.json.get("input_values")
        accountId = iv.get("account_id")
        accountSecret = iv.get("account_secret")
        # if not (accountId and accountSecret):
        #     log.warn("Must specify both account_id and account_secret")
        #     return Response("Must specify account_id and account_secret"), 500
        r = checkIntercomMsgConfigure(accountId, accountSecret)
        if r[1] != 200:
            log.warn("check failed. (%s)", r)
            canvas = intercom_messenger.getConfigureCanvas(
                msg="Your credentials could not be validated. Please make sure your account_id is correct and your account is active.")
            res = json.dumps(canvas)
        else:
            # Things check out. Now add app_id -> user_id mapping.
            putIntercomAppIdAccountIdMap(appId, accountId, accountSecret)
            res = json.dumps({"results": request.json.get("input_values")})
    else:
        canvas = intercom_messenger.getConfigureCanvas(cfg.INTERCOM_SIGNUP_MSG)
        res = json.dumps(canvas)
    assert res is not None
    return Response(res), 200

# Used for testing intercom integration by having a bunch of buttons that test
# different functionalities of intercom apps.
@app.route("/v2/intercom/sampleapp", methods=['GET', 'POST'])
def sampleapp():
    log.info("sampleapp called")
    canvas = intercom_messenger.getSampleAppCanvas()
    log.info("canvas (%s): %s", type(canvas), canvas)
    c2 = canvas.get("canvas")
    #c2 = canvas.content
    res = json.dumps(c2)
    log.info("SAMPLEAPP returning: %s", res)
    return Response(res), 200

def _getValueFromAgentUserMessages(key, configJson, defaultValue=None):
    _tmp = configJson.get("config_json", {}).get("params", {}).get("user_messages")
    userMsg = None
    if _tmp:
        for e in _tmp:
            if e.get("key") == key:
                return e.get("value")
    return defaultValue

@app.route("/v2/intercom/startinit", methods=['GET', 'POST'])
def startinit():
    log.info("startinit called")
    log.info(request.json)
    #contentUrl = request.json.get("canvas", {}).get("content_url")
    #if not contentUrl:
    #    raise Exception("Did not get expected canvas input.")
    requestUrl = request.url
    appId = request.json.get("app_id")
    if not appId:
        raise Exception("Did not find app_id")
    configJson = _fetchAgentJsonSpec(appId)
    if not configJson:
        raise Exception("could not find agent for appid %s" % (appId,))

    userMsg = _getValueFromAgentUserMessages(
        "intercomMessengerHomeScreenWelcomeMessage", configJson)
    log.info("got intercom frontpage msg: %s", userMsg)
    parts = urllib.parse.urlparse(requestUrl)
    widgetPageUrl = urllib.parse.urlunparse(
        #(parts[0], parts[1], f"/widget_page?app_id={appId}", "", "", "")
        ("https", parts[1], f"/widget_page?app_id={appId}", "", "", "")
    )
    pinConfig = configJson.get("config_json", {}).get("params", {}).get("pin_json", [])
    log.info("pinConfig: %s", pinConfig)
    canvas = None
    if pinConfig:
        canvas = intercom_messenger.getStartInitCanvasWithPinnedItems(
            widgetUrl=widgetPageUrl, pinnedItems=pinConfig, userMsg=userMsg)
    else:
        canvas = intercom_messenger.getStartInitCanvas(
            widgetUrl=widgetPageUrl, userMsg=userMsg)
    log.info("canvas (%s): %s", type(canvas), canvas)
    c2 = canvas.get("canvas")
    res = json.dumps(c2)
    log.info("startinit returning: %s", res)
    return Response(res), 200

@app.route("/v2/intercom/submit", methods=['GET', 'POST'])
def v2_intercom_submit():
    return doIntercomMsgNativeApp()

def doIntercomMsgNativeApp():
    requestStartTime = time.time()
    log.info("## submit ##")
    intercomEvent = request.json
    _pprint(intercomEvent)
    canvas = None

    app_id = request.json.get("app_id")
    if not app_id:
        return Response(json.dumps({"msg":"no app_id found"}), 500)
    # TODO(im): When app is deployed, below code will get the json spec.
    # For now, just hardcode.
    #agentDeploymentMeta = ads.getJsonSpec(app_id, "intercom_messenger")
    #log.info("agentDeploymentMeta: %s", agentDeploymentMeta)
    agentDeploymentMeta = getIntercomAgentDeploymentMeta(app_id)
    if not agentDeploymentMeta:
        log.warn("No agent for app_id: %s. Dropping this event.", app_id)
        return Response(json.dumps({"msg":"bad app_id"})), 500

    resp = _intercom_msg_agent_handler(agentDeploymentMeta, request.json, app_id)
    log.info("resp: %s", resp)
    #if (component_id == "button-back"):
    #canvas = intercom_messenger.getSampleAppCanvas()
    #else:
    #    canvas = intercom_messenger.getSearchResultsCanvas()
    #res = json.dumps(canvas)
    res = json.dumps(resp)
    log.info("-- response --")
    log.info("res: %s", res)
    #_pprint(res)

    # DEBUG
    #_tmp1 = intercom_messenger.getSampleAppCanvas()
    #res = json.dumps(_tmp1)
    #log.info("res: %s", res)

    requestEndTime = time.time()
    log.info("REQUEST TIME: %s", requestEndTime - requestStartTime)
    return Response(res), 200


@app.route("/v2/intercom/initialize", methods=['GET', 'POST'])
def v2_intercom_initialize():
    """
    When a card is being added, Intercom POSTs a request to the Messenger App’s
    # initialize_url with the card creation parameters gathered from the teammat
    e. The payload is in the following form:
    {
      card_creation_options: {
       <set of key-value pairs>
    },
      app_id: <string id_code of the app using the card>
    }

    The developer returns a response in the following format

    {
      canvas: <Canvas object>
    }

    """
    log.info("## initialize ##")
    _pprint(request.json)
    #keyframe.utils.pretty(request.__dict__)
    log.info("URL: %s", request.url)
    c = intercom_messenger.getLiveCanvas(request.url)
    #c = intercom_messenger.getSampleAppCanvas()
    res = json.dumps(c)
    log.info("INITIALIZE returning: %s", res)
    return Response(res), 200

@app.route("/v2/intercom/submit_sheet", methods=['GET', 'POST'])
def v2_intercom_submit_sheet():
    log.info("## submit_sheet ##")
    _pprint(request.json)
    res = json.dumps({})
    return Response(res), 200

@app.route("/v2/intercom/debug", methods=['GET'])
def intercom_debug():
    appId = request.args.get("app_id")
    if not appId:
        return Response("Could not get app_id"), 500
    appIdAccountIdMap = getIntercomAppIdAccountIdMap(appId)
    agentDeploymentMeta = getIntercomAgentDeploymentMeta(appId)
    ret = {
        "appIdAccountIdMap": appIdAccountIdMap,
        "agentDeploymentMeta": agentDeploymentMeta
        }
    return jsonify(ret)

########### ---- end intercom configuration ------ #############3

def print_request_details(**kwargs):
    print("DICT: %s" % (request.__dict__,))
    print("\nDATA (%s): %s" % (type(request.data), request.data,))
    print("\n\nFORM (%s): %s" % (type(request.url), request.form,))
    print("\n\nrequest.url: %s" % (request.url,))
    print("\n\n\nrequest.method: %s" % (request.method,))
    print("\n\n\n\nrequest.headers: %s" % (request.headers,))
    if request.json:
        print("\n\nrequest.json: (%s) %s" % (
            type(request.json), request.json))
    print("kwargs: %s" % (kwargs,))


if __name__ == "__main__":
    usage = "gbot.py [cmd/http] [file/db] <accountId> <agentId> [file: <path to json spec>]"
    assert len(sys.argv) > 2, usage
    keyframe.logservice.setupHandlers()

    d = {}
    cmd = sys.argv[1] # cmd/http/script
    runtype = sys.argv[2] # file/db

    log.info("(++) cmd: %s, runtime: %s", cmd, runtype)
    jsonFile = None
    agentId = None
    accountId = None
    #accountSecret = None

    if len(sys.argv) > 3:
        accountId = sys.argv[3]
    if len(sys.argv) > 4:
        agentId = sys.argv[4]

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
        log.debug("config_json: %s", d)

    if cmd == "cmd":
        c = generic_cmdline.GenericCmdlineHandler(config_json=d, accountId=accountId, agentId=agentId, kvStore=getKVStore(), cfg=cfg)
        c.begin()

    elif cmd == "script":
        scriptFile = sys.argv[6]
        c = generic_cmdline.ScriptHandler(config_json=d, accountId=accountId, agentId=agentId, kvStore=getKVStore(), cfg=cfg)
        c.scriptFile(scriptFile=scriptFile)
        num_errors = c.executeScript()
        if num_errors > 0:
            log.error("num_errors: %s", num_errors)
            sys.exit(1)

    elif cmd == "http":
        app.config["cmd_mode"] = cmd
        app.config["run_mode"] = runtype
        app.config["config_json"] = d
        app.run(debug=True)  # default port is 5000

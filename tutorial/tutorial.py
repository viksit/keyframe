from __future__ import print_function
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


# Create an API object to inject into our bot
apicfg = {
    "account_id": "1so4xiiNq29ElrbiONSsrS",
    "account_secret": "a33efcebdc44f243aac4bfcf7bbcc24c29c90587"
}
# Intent and entity models that we're using
INTENT_MODEL_ID = "0dfb5f1fe1c54466bd31503cc4dd82e4"

# Establish a global API connection
api = client.connect(apicfg)
api.set_intent_model(INTENT_MODEL_ID)

# KV Store
# TODO:
# Initialize via a configuration file
kvStore = store_api.get_kv_store(
    #store_api.TYPE_LOCALFILE,
    #store_api.TYPE_DYNAMODB,
    store_api.TYPE_INMEMORY,
    config.Config())


bot = BaseBot(api=api, kvStore=kvStore)

# Actions
@bot.intent2("create")
class CreateIntentActionObject(ActionObject):

    @bot.slot("create", ["person", "optional", "PERSON"])
    class PersonSlot(Slot):

        def prompt(self):
            return "who do you want to set up the meeting with?"

    @bot.slot("create", ["time", "optional", "DATE"])
    class DateSlot(Slot):

        def prompt(self):
            return "and when?"


    @bot.slot("create", ["city", "optional", "GPE"])
    class CitySlot(Slot):

        def prompt(self):
            return "which city do you want to meet in?"


    @bot.slot("create", ["bank", "optional", "ORG"])
    class BankSlot(Slot):

        def prompt(self):
            return "which bank do you want to meet at?"


    # Won't get called till slots are filled.
    def process(self):

        # At this point, any slots should be filled up.
        for slot in self.slotObjects:
            print("(process) slot: ", slot.entityType, slot.filled, slot.value)

        # Process the response
        message = "Sure, I'll create the meeting for you"
        #resp = _returnResponse(e, message)
        resp = message

        # Send it back on this channel
        responseType = messages.ResponseElement.RESPONSE_TYPE_RESPONSE
        cr = messages.createTextResponse(self.canonicalMsg,
                                         resp,
                                         responseType)
        self.channelClient.sendResponse(cr)
        return BaseBot.REQUEST_STATE_PROCESSED

@bot.intent("cancel")
class CancelIntentActionObject(ActionObject):

    def process(self):

        # Process the response
        #e = self.apiResult.entities.entity_dict.get("builtin", {})
        message = "Sure, I'll cancel the meeting for you"
        #resp = _returnResponse(e, message)
        resp = message
        # Send it back on this channel
        responseType = self.messages.ResponseElement.RESPONSE_TYPE_RESPONSE
        cr = self.messages.createTextResponse(self.canonicalMsg,
                                              resp,
                                              responseType)
        self.channelClient.sendResponse(cr)



class CalendarBotHTTPAPI(BotAPI):

    def getBot(self):
        self.bot = bot
        return bot

## Deployment for command line

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



# -- Deployment for lambda
class CalendarBotHTTPAPI(BotAPI):
    def getBot(self):
        self.bot = bot
        return bot

app = Flask(__name__)
@app.route("/localapi", methods=["GET", "POST"])
def localapi():
    event = {
        "channel": messages.CHANNEL_HTTP_REQUEST_RESPONSE,
        "request-type": request.method,
        "body": request.json
    }
    r = CalendarBotHTTPAPI.requestHandler(
        event=event,
        context={})
    return Response(str(r)), 200

@app.route('/ping', methods=['GET', 'POST'])
def ping():
    print("PING")
    print(request.data)
    return Response('ok'), 200

if __name__ == "__main__":
    # Run the command line version
    c = CalendarCmdlineHandler()
    c.begin()

    # OR uncomment this to run this via flask
    # app.run(debug=True)

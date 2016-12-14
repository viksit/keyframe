from __future__ import print_function
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

# Custom stuff
from model import IntentModel
from model import EntityModel

# TODO(viksit): put configuraton object into a nicer format.
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
    store_api.TYPE_DYNAMODB,
    #store_api.TYPE_INMEMORY,
    config.Config())


bot = BaseBot(api=api, kvStore=kvStore)


@bot.intent(IntentModel.fivedig)
class DigitActionObject(ActionObject):
    def process(self):
        resp = "Some 5 digit number was shown!!!!!!!"
        return self.respond(resp)

@bot.intent(IntentModel.greeting)
class GreetingActionObject(ActionObject):

    def process(self):
        resp = "Hi there!"
        return self.respond(resp)

# Actions
@bot.intent(IntentModel.create)
class CreateIntentActionObject(ActionObject):

    class PersonSlot(Slot):

        # TODO(viksit): right now, all slots need to have these 4 things
        # In the future, we can have default values at the Slot level but not sure
        # what this should be.

        entity = EntityModel.person

        # Ignored right now.
        required = False

        # NOTE(viksit):
        # parseOriginal should either be True in all slots, or false in all.
        # this is because of internal implementation reasons and also I'm not sure
        # if the extra complexity of supporting it makes sense.
        parseOriginal = True

        # This means that any response the user makes need to contain an entity which
        # our system can match to (PERSON)
        parseResponse = True

        def prompt(self):
            return "who do you want to set up the meeting with?"

    class DateSlot(Slot):
        entity = EntityModel.mydate
        parseOriginal = True
        parseResponse = False
        required = False

        def prompt(self):
            return "when do you want the meeting to be set up?"


    class CitySlot(Slot):
        entity = EntityModel.mycity
        parseOriginal = True
        parseResponse = False
        required = False

        def prompt(self):
            return "which city do you want to meet in?"


    class BankSlot(Slot):
        entity = EntityModel.mybank
        parseOriginal = True
        parseResponse = False
        required = False

        def prompt(self):
            return "which bank do you want to meet at?"

    # Won't get called till slots are filled.
    def process(self):
        message = "Sure, I'll create the meeting for you with : {0} {1} {2} {3}".format(*[i.value for i in self.slotObjects])
        resp = message
        return self.respond(resp)

@bot.intent(IntentModel.cancel)
class CancelIntentActionObject(ActionObject):

    def process(self):
        message = "Sure, I'll cancel the meeting for you"
        resp = message
        return self.respond(resp)

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
    #app.run(debug=True)

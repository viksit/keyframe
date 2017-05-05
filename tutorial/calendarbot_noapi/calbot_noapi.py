from __future__ import print_function
import sys
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

# Custom stuff
from model import IntentModel
from model import EntityModel

# TODO:
# Initialize via a configuration file
kvStore = store_api.get_kv_store(
    #store_api.TYPE_LOCALFILE,
    store_api.TYPE_DYNAMODB,
    #store_api.TYPE_INMEMORY,
    config.getConfig())


bot = BaseBot(kvStore=kvStore)


@bot.intent(IntentModel.fivedig)
class DigitActionObject(ActionObject):
    def process(self):
        resp = "Some 5 digit number was shown!!!!!!!"
        self.respond(resp)
        return constants.BOT_REQUEST_STATE_PROCESSED

@bot.intent(IntentModel.greeting)
class GreetingActionObject(ActionObject):

    class PhoneSlot(Slot):
        entity = EntityModel.myphone
        required = "optional"
        parseResponse = True
        parseOriginal = False

        def prompt(self):
            return "Whats your phone number yo?"

    class EmailSlot(Slot):
        entity = EntityModel.myemail
        required = "optional"
        parseResponse = True
        parseOriginal = False

        def prompt(self):
            return "and whats your email?"


    class UserSlot(Slot):
        entity = EntityModel.user
        required = "optional"
        parseResponse = False
        parseOriginal = False

        def prompt(self):
            return "Who are you?"

    def process(self):
        print("slots: ", self.filledSlots)
        resp = "Hi there, {user_slot}, your phone is {phone_slot} and your email is {email_slot}!".format(**self.filledSlots)
        self.respond(resp)
        return constants.BOT_REQUEST_STATE_PROCESSED


# ------

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
        parseOriginal = False

        # This means that any response the user makes need to contain an entity which
        # our system can match to (PERSON)
        parseResponse = False

        def prompt(self):
            return "who do you want to set up the meeting with?"

    class DateSlot(Slot):
        entity = EntityModel.mydate
        parseOriginal = False
        parseResponse = False
        required = False

        def prompt(self):
            return "when do you want the meeting to be set up?"


    class CitySlot(Slot):
        entity = EntityModel.mycity
        parseOriginal = False
        parseResponse = False
        required = False

        def prompt(self):
            return "which city do you want to meet in?"


    class BankSlot(Slot):
        entity = EntityModel.mybank
        parseOriginal = False
        parseResponse = False
        required = False

        def prompt(self):
            return "which bank do you want to meet at?"

    # Won't get called till slots are filled.
    def process(self):
        message = "(example) Sure, I'll create the meeting for you with : {date_slot} {person_slot} {bank_slot} {city_slot}".format(**self.filledSlots)
        resp = message
        self.respond(resp)
        return constants.BOT_REQUEST_STATE_PROCESSED

@bot.intent(IntentModel.cancel)
class CancelIntentActionObject(ActionObject):

    def process(self):
        message = "Sure, I'll cancel the meeting for you"
        resp = message
        self.respond(resp)
        return constants.BOT_REQUEST_STATE_PROCESSED

# -----
@bot.intent(IntentModel.default)
class DefaultActionObject(ActionObject):

    def process(self):
        resp = "Looks like I didn't get what you said!"
        self.respond(resp)
        return constants.BOT_REQUEST_STATE_PROCESSED

# Deployment for command line
class CalendarCmdlineHandler(BotCmdLineHandler):
    def init(self):
        # channel configuration
        cf = config.getConfig()
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
    if len(sys.argv) > 1 and sys.argv[1] == 'cmd':
        # Run the command line version
        c = CalendarCmdlineHandler()
        c.begin()
    else:
        # OR uncomment this to run this via flask
        app.run(debug=True)

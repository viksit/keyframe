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

# Custom stuff
from model import IntentModel
from model import EntityModel

# TODO:
# Initialize via a configuration file
kvStore = store_api.get_kv_store(
    #store_api.TYPE_LOCALFILE,
    store_api.TYPE_DYNAMODB,
    #store_api.TYPE_INMEMORY,
    config.Config())


bot = BaseBot(kvStore=kvStore)


@bot.intent(IntentModel.fivedig)
class DigitActionObject(ActionObject):
    def process(self):
        resp = "Some 5 digit number was shown!!!!!!!"
        # Send it back on this channel
        responseType = messages.ResponseElement.RESPONSE_TYPE_RESPONSE
        cr = messages.createTextResponse(self.canonicalMsg,
                                         resp,
                                         responseType)
        self.channelClient.sendResponse(cr)
        return BaseBot.REQUEST_STATE_PROCESSED

@bot.intent(IntentModel.greeting)
class GreetingActionObject(ActionObject):

    class UserSlot(Slot):
        entity = EntityModel.user
        parseResponse = True

        def prompt(self):
            return "Who are you?"

    def process(self):
        print("slots: ", self.slotObjects)
        resp = "Hi there, %s!" % (self.slotObjects[0].value)
        return self.respond(resp)


@bot.intent(IntentModel.default)
class DefaultActionObject(ActionObject):

    def process(self):
        resp = "Looks like I didn't get what you said!"
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
    # c = CalendarCmdlineHandler()
    # c.begin()

    # OR uncomment this to run this via flask
    app.run(debug=True)

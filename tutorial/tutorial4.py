from __future__ import print_function
from os.path import expanduser, join

from pymyra.api import client

from keyframe.main import BaseBot, Actions, BotCmdLineHandler,\
    ActionObject, BaseBotv2
from keyframe import channel_client
from keyframe import messages
from keyframe import config

############## Tutorial code ####################

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


# What do you want to do?
# build a calendar bot

# what should this bot do?
# create a meeting, cancel a meeting and modify a meeting.
# it should connect to google calendar and then do something with it.


# TODO(viksit): support classes and function decorators so that quick start can be easy.

bot = BaseBotv2(api=api)

# @bot.slot(..)
@bot.intent("create")
class CreateActionObject(ActionObject):

    def _returnResponse(self, entities, message):

        e = entities
        if "PERSON" in e:
            person = [i.get("text") for i in e.get("PERSON")]
            person_text = ""
            if len(person) > 1:
                person_text = " and ".join(person)
            else:
                person_text = person[0]
            message += " with %s" % person_text

        if "DATE" in e:
            tm = [i.get("date") for i in e.get("DATE")]
            tm_text = ""
            if len(tm) >= 1:
                tm_text = tm[0]
            message += " at %s." % (tm_text)

        return message

    def process(self):
        # Process the response
        e = self.apiResult.entities.entity_dict.get("builtin", {})
        message = "Sure, I'll create the meeting for you"
        resp = self._returnResponse(e, message)

        # Send it back on this channel
        responseType = self.messages.ResponseElement.RESPONSE_TYPE_RESPONSE
        cr = self.messages.createTextResponse(self.canonicalMsg,
                                         resp,
                                         responseType)
        self.channelClient.sendResponse(cr)


@bot.intent("cancel")
class CancelActionObject(ActionObject):

    def _returnResponse(self, entities, message):

        e = entities
        if "PERSON" in e:
            person = [i.get("text") for i in e.get("PERSON")]
            person_text = ""
            if len(person) > 1:
                person_text = " and ".join(person)
            else:
                person_text = person[0]
            message += " with %s" % person_text

        if "DATE" in e:
            tm = [i.get("date") for i in e.get("DATE")]
            tm_text = ""
            if len(tm) >= 1:
                tm_text = tm[0]
            message += " at %s." % (tm_text)

        return message

    def process(self):
        # Process the response
        e = self.apiResult.entities.entity_dict.get("builtin", {})
        message = "Sure, I'll cancel the meeting for you"
        resp = self._returnResponse(e, message)

        # Send it back on this channel
        responseType = self.messages.ResponseElement.RESPONSE_TYPE_RESPONSE
        cr = self.messages.createTextResponse(self.canonicalMsg,
                                         resp,
                                         responseType)
        self.channelClient.sendResponse(cr)


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

if __name__ == "__main__":
    c = CalendarCmdlineHandler()
    c.begin()

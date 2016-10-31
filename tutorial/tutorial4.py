from __future__ import print_function
from os.path import expanduser, join

from pymyra.api import client

from keyframe.main import BaseBot, Actions, BotCmdLineHandler
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


# Create the bot itself

# Create an actions object to register intent handlers
# TODO(viksit): rename this to "Bot"

actions = Actions()

# Base bot class
class CalendarBot(BaseBot):

    welcomeMessage = "Welcome to calendar bot! I can help you create and cancel meetings. Try 'set up a meeting with Jane' or 'cancel my last meeting' to get started."

    def __init__(self, *args, **kwargs):
        super(CalendarBot, self).__init__(*args, **kwargs)

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

    # Example of a simple handler with a threshold, and a fallback intent
    # apiResult is an object that is available to all functions decorated by
    # @action.intent.

    @actions.intent("cancel", threshold=(0.4, "unknown"))
    def cancelHandler(self):
        e = apiResult.entities.entity_dict.get("builtin", {})
        msg = "Sure, I'll cancel the meeting for you"
        return self._returnResponse(e, msg)

    # Example of a simple handler with an apiResult
    @actions.intent("create")
    def createHandler(self):
        e = apiResult.entities.entity_dict.get("builtin", {})
        msg = "I can help create a meeting for you"
        return self._returnResponse(e, msg)

    # Example of a simple handler without an apiResult
    @actions.intent("help")
    def helpHandler(self):
        return "Help message for this bot"

    @actions.intent("unknown")
    def unknownHandler(self):
        return "unknown intent or low score %s, %s"\
            % (apiResult.intent.label, apiResult.intent.score)

    def process(self, canonicalMsg):
        message = actions.handle(canonicalMsg=canonicalMsg,
                                 myraAPI=self.api)
        self.createAndSendTextResponse(
            canonicalMsg,
            message,
            messages.ResponseElement.RESPONSE_TYPE_RESPONSE)

class CalendarCmdlineHandler(BotCmdLineHandler):

    def init(self):

        cf = config.Config()
        channelClient = channel_client.getChannelClient(
            channel=messages.CHANNEL_CMDLINE,
            requestType=None,
            config=cf)

        self.bot = CalendarBot(api=api,
                               actions=actions,
                               channelClient=channelClient)

if __name__ == "__main__":
    c = CalendarCmdlineHandler()
    c.begin()

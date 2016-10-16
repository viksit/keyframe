from __future__ import print_function
from os.path import expanduser, join

from pymyra.api import client
from pymyra.lib.keyframe import *
from pymyra.lib.channel_client import *
from pymyra.lib.messages import *

############## Tutorial code ####################

# Configuration for Myra's API
# Create the API config object from a configuration file
# This gets the config from /Users/<username>/.myra/settings.conf
CONF_FILE = join(expanduser('~'), '.pymyra', 'settings.conf')
config = client.get_config(CONF_FILE)

# Intent and entity models that we're using
INTENT_MODEL_ID = "27c71fe414984927a32ff4d6684e0a73"
# prod "b4a5ce9b075e416bb1e8968eea735fa6"

# Establish a global API connection
api = client.connect(config, debug=False)
api.set_intent_model(INTENT_MODEL_ID)

# Create an actions object to register intent handlers
actions = Actions()


class CalendarBot(BaseBot):

    welcomeMessage = "Welcome to calendar bot! I can help you create and cancel meetings. Try 'set up a meeting with Jane' or 'cancel my last meeting' to get started."

    def __init__(self, *args, **kwargs):
        super(CalendarBot, self).__init__(*args, **kwargs)

    # Example of a simple handler with a threshold, and a fallback intent
    # apiResult is an object that is available to all functions decorated by
    # @action.intent.

    @actions.intent("cancel", threshold=(0.4, "unknown"))
    def cancelHandler(self):
        e =  apiResult.entities.entity_dict.get("builtin", {})
        message = "Sure, I'll cancel the meeting for you"
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

    # Example of a simple handler with an apiResult
    @actions.intent("create")
    def createHandler(self):
        e = apiResult.entities.entity_dict.get("builtin", {})
        message = "I can help create a meeting for you"
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
        cr = messages.createTextResponse(canonicalMsg, message, responseType)
        self.channelClient.sendResponse(cr)

class CalendarCmdlineHandler(BotCmdLineHandler):

    def init(self):
        channelClient = ChannelClient()
        self.bot = CalendarBot(api=api,
                               actions=actions,
                               channel=channelClient)

if __name__ == "__main__":
    #bot = CalendarBot(api=api, actions=actions)
    #c = CmdLineHandler(bot)
    #c.begin(bot.welcomeMessage)
    c = CalendarCmdlineHandler()
    c.begin()

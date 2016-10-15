from __future__ import print_function
from os.path import expanduser, join
from myra_client import clientv2
from utils import Actions, CmdLineHandler

"""
# TODO
- clean up the entity response
- merge time from spacy and parse datetime
- built in vs user defined


"""
############## Tutorial code ####################

# Configuration for Myra's API
# Create the API config object from a configuration file
# This gets the config from /Users/<username>/.myra/settings.conf
CONF_FILE = join(expanduser('~'), '.myra', 'settings.conf')
config = clientv2.get_config(CONF_FILE)

# Intent and entity models that we're using
INTENT_MODEL_ID = "b4a5ce9b075e416bb1e8968eea735fa6"
ENTITY_MODEL_ID = "4911dc1f0005408881e08a05dd998b0f"

# Establish a global API connection
api = clientv2.connect(config)
api.set_intent_model(INTENT_MODEL_ID)
api.set_entity_model(ENTITY_MODEL_ID)

# Create an actions object to register intent handlers
actions = Actions()

class CalendarBot(object):

    welcome_message = "Welcome to calendar bot! I can help you create and cancel meetings. Try 'set up a meeting with Jane' or 'cancel my last meeting' to get started."

    def __init__(self):
        pass


    # Example of a simple handler with a threshold, and a fallback intent
    @actions.intent("cancel", threshold=(0.4, "unknown"))
    def cancel_handler(self):
        e =  api_result.entities.entities.get("builtin", {})
        message = "Sure, I'll cancel the meeting for you"
        if "PERSON" in e:
            person = [i.get("text") for i in e.get("PERSON")]
            person_text = ""
            if len(person) > 1:
                person_text = " and ".join(person)
            else:
                person_text = person[0]
            message += " with %s" % person_text
        if "time" in e and e.get("time") is not None:
            tm = e.get("time")[0][0]
            message += " at %s." % (tm)
        return message


    # Example of a simple handler with an api_result
    @actions.intent("create")
    def create_handler(self):
        e = api_result.entities.entities.get("builtin", {})
        message = "I can help create a meeting for you"
        if "PERSON" in e:
            person = [i.get("text") for i in e.get("PERSON")]
            person_text = ""
            if len(person) > 1:
                person_text = " and ".join(person)
            else:
                person_text = person[0]
            message += " with %s" % person_text
        if "time" in e and e.get("time") is not None:
            tm = e.get("time")[0][0]
            message += " at %s." % (tm)
        return message

    # Example of a simple handler without an api_result
    @actions.intent("help")
    def help_handler(self):
        return "Help message for this bot"

    @actions.intent("unknown")
    def unknown_handler(self):
        return "unknown intent or low score %s, %s" % (api_result.intent.label, api_result.intent.score)

    def process(self, user_input):
        api_result = api.get(user_input)
        message = actions.handle(api_result)
        print(">> ", message)


if __name__ == "__main__":
    bot = CalendarBot()
    c = CmdLineHandler(bot)
    c.begin(bot.welcome_message)

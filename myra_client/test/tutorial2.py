from __future__ import print_function
from os.path import expanduser, join
from myra_client import clientv2
from utils import Actions, CmdLineHandler


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
    @actions.intent("cancel", threshold=(0.7, "unknown"))
    def cancel_handler(self):
        return ("cancel", api_result.intent.score)

    # Example of a simple handler with an api_result
    @actions.intent("create")
    def create_handler(self):
        return ("create", api_result.entities.entities)

    # Example of a simple handler without an api_result
    @actions.intent("help")
    def help_handler(self):
        return "help"

    @actions.intent("unknown")
    def unknown_handler(self):
        return "unknown intent or low score"

    def process(self, user_input):
        api_result = api.get(user_input)
        message = actions.handle(api_result)
        print(">> ", message)


if __name__ == "__main__":
    bot = CalendarBot()
    c = CmdLineHandler(bot)
    c.begin(bot.welcome_message)

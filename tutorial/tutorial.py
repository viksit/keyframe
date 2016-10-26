from os.path import expanduser, join


from pymyra.api import client
from pymyra.lib.keyframe import CmdLineHandler

# Create the API config object from a configuration file
# This gets the config from /Users/<username>/.myra/settings.conf

CONF_FILE = join(expanduser('~'), '.pymyra', 'settings.conf')
config = client.get_config(CONF_FILE)

# TODO(viksit) move this to an actual ID that someone will replace
INTENT_MODEL_ID = "27c71fe414984927a32ff4d6684e0a73"
#ENTITY_MODEL_ID = "4911dc1f0005408881e08a05dd998b0f"

# Establish a global API connection
api = client.connect(config)
api.set_intent_model(INTENT_MODEL_ID)
#api.set_entity_model(ENTITY_MODEL_ID)


class Actions(object):

    def __init__(self):
        # Ultimately, given a model, we ought to be able to
        # get a list of intents from an API
        self.intent_map = {
            "cancel": self.cancel_handler,
            "create": self.create_handler,
            "help": self.help_handler,
            "unknown": self.unknown_handler
        }

    def handle(self, **kwargs):
        result = kwargs.get("result")
        intent = result.intent
        if intent.label not in self.intent_map:
            intent.label = "unknown"
            intent.score = 1
        return self.intent_map.get(intent.label)(**kwargs)

    def cancel_handler(self, **kwargs):
        result = kwargs.get("result")
        return "cancel meeting %s %s" % (result.intent.label, result.intent.score)

    def create_handler(self, **kwargs):
        result = kwargs.get("result")
        return "create meeting  %s %s" % (result.intent.label, result.intent.score)

    def help_handler(self, **kwargs):
        result = kwargs.get("result")
        return "This is some help  %s %s" % (result.intent.label, result.intent.score)

    def unknown_handler(self, **kwargs):
        result = kwargs.get("result")
        return "I'm sorry I don't know how to handle this\ %s %s" % (
            result.intent.label, result.intent.score)


class CalendarBot(object):

    def __init__(self):
        self.actions = Actions()

    def process(self, user_input):
        result = api.get(user_input)
        message = self.actions.handle(result=result)
        print(">> ", message)

if __name__ == "__main__":
    bot = CalendarBot()
    c = CmdLineHandler(bot)
    c.begin()

import ConfigParser
import inspect

################# Library code #####################

#####################################
# Utilities for the Myra API tutorial
#####################################

class CmdLineHandler(object):

    def __init__(self, bot):
        self.bot = bot

    # Begin your command line loop
    def begin(self, start_message=None):
        if start_message:
            print(">> ", start_message)
        while True:
            try:
                user_input = raw_input("> ")
                if not user_input:
                    continue
                self.process_message(user_input)
            except (KeyboardInterrupt, EOFError, SystemExit):
                break

    # Handle incoming messages and return the response
    def process_message(self, user_input):
        return self.bot.process(user_input)


####################################################
# Simple Intent - handler mapping
####################################################

class Actions():
    def __init__(self):
        self.intents = {}
        self.intent_thresholds = {}

    def intent(self, intent_str, threshold=(None, "unknown")):
        def decorator(f):
            self.intents[intent_str] = f
            if threshold:
                self.intent_thresholds[intent_str] = threshold
            return f
        return decorator

    def handle(self, api_result):
        intent_str = api_result.intent.label
        intent_score = api_result.intent.score
        if intent_str in self.intents:
            if intent_str in self.intent_thresholds:
                handler_function = self.intents.get(intent_str)
                if intent_score < self.intent_thresholds.get(intent_str)[0]:
                    handler_function = self.intents.get(self.intent_thresholds.get(intent_str)[1])
                # Make the api_result available within the scope of the intent handler.
                # NOTE: This dictionary update is NOT thread safe, and is shared by all functions
                # in the given namespace.
                handler_function.func_globals['api_result'] = api_result
                return handler_function(self)
        else:
            raise ValueError("Intent '{}'' has not been registered".format(intent_str))


class MyraConfig(object):
    def __init__(self, config_file = None):
        self.config_file = config_file
        if not self.config_file:
            self.config_file = "./settings.conf"
        self.config = ConfigParser.ConfigParser()
        self.config.read(self.config_file)

    def get(self, section):
        res = {}
        options = self.config.options(section)
        for option in options:
            try:
                res[option] = self.config.get(section, option)
                if res[option] == -1:
                    pass # Skip
            except:
                print("exception on %s!" % option)
                res[option] = None
        return res




############ End library code ###########################

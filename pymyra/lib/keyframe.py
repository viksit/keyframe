from __future__ import print_function
import inspect

import messages

################# Library code #####################

#####################################
# Utilities for the Myra API tutorial
#####################################

# class CmdLineHandler(object):
#     """ Simple terminal REPL for bots
#     """

#     def __init__(self, bot):
#         self.bot = bot

#     # Begin your command line loop
#     def begin(self, startMessage=None):
#         if startMessage:
#             print(">> ", startMessage)
#         while True:
#             try:
#                 userInput = raw_input("> ")
#                 if not userInput:
#                     continue
#                 self.processMessage(userInput)
#             except (KeyboardInterrupt, EOFError, SystemExit):
#                 break

#     # Handle incoming messages and return the response
#     def processMessage(self, userInput):
#         return self.bot.process(userInput)
#################################################################

class CmdLineHandler(object):
    def __init__(self, userId=None):
        self.userId = userId
        if not self.userId:
            self.userId = "bot_arch_msghandler_user"
        self.init()

    def init(self):
        # Override to initialize other MessageHandler variables.
        pass

    def begin(self):
        while True:
            try:
                userInput = raw_input("> ")
                if not userInput:
                    continue
                isCmd = self.checkCmds(userInput)
                if isCmd:
                    continue
                self.processMessage(userInput)
            except (KeyboardInterrupt, EOFError, SystemExit):
                break

    # Handle incoming messages and return the response
    def processMessage(self, userInput):
        raise NotImplementedError()

    def checkCmds(self, userInput):
        if userInput.startswith("/user_id"):
            if len(userInput.split()) == 2:
                self.userId = userInput.split()[1]
                print("user_id set to: %s" % (self.userId,))
            else:
                print("usage: /user_id <user-id>")
            return True
        return False


class BotCmdLineHandler(CmdLineHandler):

    def init(self):
        self.bot = None  # Create your bot here by overriding init in your class.
        raise NotImplementedError()

    def processMessage(self, userInput):
        canonicalMsg = messages.CanonicalMsg(
            channel=messages.CHANNEL_CMDLINE,
            httpType=None,
            userId=self.userId,
            text=userInput)
        self.bot.process(canonicalMsg)


class Actions(object):
    """ Intent-Action mapping function decorators
    """

    def __init__(self):
        self.intents = {}
        self.intentThresholds = {}
        self.keywordIntents = {}
        self.regexIntents = {}

    def regex_intent(self, intentStr):
        def decorator(f):
            self.regexIntents[intentStr] = f
            return f
        return decorator

    # TODO(viksit): check that keyword and model intents don't overlap

    def keyword_intent(self, intentStr):
        def decorator(f):
            self.keywordIntents[intentStr] = f
            return f
        return decorator

    def intent(self, intentStr, threshold=(None, "unknown")):
        def decorator(f):
            self.intents[intentStr] = f
            if threshold:
                self.intentThresholds[intentStr] = threshold
            return f
        return decorator

    def handle(self, **kwargs):
        """ Support keyword intent, model intent and regex intent
        handling
        """
        userInput = kwargs.get("userInput")
        myraAPI = kwargs.get("myraAPI")

        # TODO(viksit): Functionality
        # Check if any given string in keyword intents is in the input
        # If it is, run that function on the input.
        # You can match : equals, contains?

        # If we got this far, then we need to run the model
        apiResult = myraAPI.get(userInput)
        intentStr = apiResult.intent.label
        intent_score = apiResult.intent.score

        if intentStr in self.intents:
            if intentStr in self.intentThresholds:
                handlerFunction = self.intents.get(intentStr)
                if intent_score < self.intentThresholds.get(intentStr)[0]:
                    handlerFunction = self.intents.get(self.intentThresholds.get(intentStr)[1])
                # Make the apiResult available within the scope of the intent handler.
                # NOTE: This dictionary update is NOT thread safe, and is shared by all functions
                # in the given namespace.
                handlerFunction.func_globals['apiResult'] = apiResult
                handlerFunction.func_globals['userInput'] = userInput
                return handlerFunction(self)
        else:
            raise ValueError("Intent '{}'' has not been registered".format(intentStr))


class BaseBot(object):

    def __init__(self, *args, **kwargs): # api, channel, ctxstore, config, actions, debug=False):
        self.api = kwargs.get("api")
        self.channel = kwargs.get("channel")
        self.ctxstore = kwargs.get("ctxstore")
        self.config = kwargs.get("config")
        self.debug = kwargs.get("debug")
        self.actions = kwargs.get("actions")

    def init(self):
        # Override to initialize stuff in derived bots
        pass










############ End library code ###########################
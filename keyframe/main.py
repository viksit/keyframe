from __future__ import print_function
import inspect
import logging

import messages
import channel_client
import fb
import uuid
from collections import defaultdict

log = logging.getLogger(__name__)

def getUUID():
   return str(uuid.uuid4()).replace("-", "")


################# Library code #####################

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


# Class based decorators
class ActionObject(object):

    def __init__(self):
        self.__clsid__ = getUUID()

        # TODO(viksit): dont make this manually assignable?
        # Dynamically injected
        self.apiResult = None
        self.canonicalMsg = None

    def process(self):
        pass

class BotState(object):
    """Serializable object for keeping bot state across requests.
    """
    def __init__(self):
        self._waiting = None  # Json-compatible structure that allows
                              # ActionObjects to be re-created.
        self._lastResult = None  # CanonicalResult
        self.changed = False
        self.debug = False

    def __repr__(self):
        return "%s" % (self.toJSONObject())

    def setDebug(self, debug):
        self.debug = debug

    def getWaiting(self):
        """Get an action object waiting for input, remove it
        from waiting, and return it (like a pop except this is not a stack).
        """
        tmp = self._waiting
        self._waiting = None
        self.changed = True
        return tmp

    def putWaiting(self, actionObjectJson):
        """Input
        actionObjectJson: (object) A json-compatible python data structure
        """
        self._waiting = actionObjectJson
        self.changed = True

    def getLastResult(self):
        return self._lastResult

    def putLastResult(self, canonicalResult):
        self._lastResult = canonicalResult
        self.changed = True

    def toJSONObject(self):
        """Return a json-compatible data structure with all of the
        data required to reconstruct this instance.
        """
        return {
            "class":self.__class__.__name__,
            "waiting":self._waiting,
            "last_result": self._lastResult
        }

    @classmethod
    def fromJSONObject(cls, jsonObject):
        """Input
        jsonObject: object as returned by toJSONObject()
        """
        assert jsonObject.get("class") == cls.__name__, \
            "bad class. data class: %s, my class: %s" % (
                jsonObject.get("class"), cls.__name__)
        botState = cls()
        botState._waiting = jsonObject.get("waiting")
        botState._lastResult = jsonObject.get("last_result")
        return botState


class Slot(object):

    def __init__(self):
        pass

    def init(self, **kwargs):
        self.name = kwargs.get("name")
        self.entityType = kwargs.get("entityType")
        self.required = kwargs.get("required")
        self.intent = kwargs.get("intent")
        self.filled = False
        self.value = None
        self.validated = False

    def get(self):
        pass

    def prompt(self):
        pass

    def validate(self):
        pass

    def reset(self):
        # Only change the modifiable stuff
        self.value = None
        self.validated = False
        self.filled = False

class BaseBotv2(object):

    def __init__(self, *args, **kwargs):

        self.api = kwargs.get("api")
        self.channelClient = kwargs.get("channelClient")
        self.ctxstore = kwargs.get("ctxstore")
        self.config = kwargs.get("config")
        self.debug = kwargs.get("debug")

        self.intentActions = {}
        self.intentThresholds = {}
        self.keywordIntents = {}
        self.regexIntents = {}
        self.intentSlots = defaultdict(lambda: [])
        # Add debug
        self.init()

        self.state = "new"
        self.onetime = False

    def init(self):
        # Override to initialize stuff in derived bots
        pass

    def setChannelClient(self, cc):
        self.channelClient = cc

    def createAndSendTextResponse(self, canonicalMsg, text, responseType=None):
        log.info("createAndSendTextResponse(%s)", locals())
        cr = messages.createTextResponse(canonicalMsg, text, responseType)
        log.info("cr: %s", cr)
        self.channelClient.sendResponse(cr)

    def errorResponse(self, canonicalMsg):
        self.createAndSendTextResponse(
            canonicalMsg, "Internal Error",
            messages.ResponseElement.RESPONSE_TYPE_RESPONSE)

    def process(self, canonicalMsg):
        return self.handle(
            canonicalMsg=canonicalMsg,
            myraAPI=self.api)

    # Decorators
    # keyword intent, regex intent
    def intent(self, intentStr, **args):
        def myfun(cls):
            wrapped = cls(**args)
            self.intentActions[intentStr] = wrapped

            # TODO(viksit): is this needed anymore?
            class Wrapper(object):
                def __init__(self, *args):
                    self.wrapped = cls(*args)
                    self.intentActions[intentStr] = self.wrapped

                def __getattr__(self, name):
                    return getattr(self.wrapped, name)
            # return class
            return Wrapper

        # return decorator
        return myfun

    # why shouldn't this be just regular keyword args?
    def slot(self, intentStr, slotList, **args):
        def myfun(cls):
            wrapped = cls()
            wrapped.init(intent=intentStr,
                         name=slotList[0],
                         required=slotList[1],
                         entityType=slotList[2])
            # TODO(viksit): error handling
            self.intentSlots[intentStr].append(wrapped)
        # return decorator
        return myfun



    def fillFrom(self, canonicalMsg, slotClasses, apiResult):
        for slotClass in slotClasses:
            slotClass.canonicalMsg = canonicalMsg
            slotClass.apiResult = apiResult
            if not slotClass.filled:
                print("trying to fill slot %s from within sentence" % slotClass.name)
                e = apiResult.entities.entity_dict.get("builtin", {})
                if slotClass.entityType in e:
                    # TODO(viksit): this needs to change to have "text" in all entities.
                    k = "text"
                    if slotClass.entityType == "DATE":
                        k = "date"
                    tmp = [i.get(k) for i in e.get(slotClass.entityType)]

                    if len(tmp) > 0:
                        slotClass.value = tmp[0]
                        slotClass.filled = True
                        print("\tslot was filled in this sentence")
                        continue
                    else:
                        print("\tslot wasn't filled in this sentence")
                        # nothing was found
                        # we'll query the user for it.
                else:
                    print("\tslot wasn't filled in this sentence")

    """
    Evaluate the given sentence to see which slots you can fill from it.
    Mark the ones that are filled
    The ones that remain unfilled are the ones that we come back to each time.
    """
    def fill(self, slotClasses, canonicalMsg, apiResult):


        print("Availble slots: ")
        for slotClass in slotClasses:
            print("\t slot, filled", slotClass.name, slotClass.filled)

        # First we should fill all possible slots from the sentence
        # For those that aren't filled, we run through this logic.

        print("self onetime: ", self.onetime)
        if not self.onetime:
            self.fillFrom(canonicalMsg, slotClasses, apiResult)
            self.onetime = True

        # Now, whats left unfilled are slots that weren't completed by the user
        # in the first go. Ask the user for input here.

        for slotClass in slotClasses:
            # TODO(viksit): add validation step here as well.
            if not slotClass.filled:
                slotClass.canonicalMsg = canonicalMsg
                slotClass.apiResult = apiResult
                print("trying to fill slot %s via user" % slotClass.name)
                print("state: ", self.state)
                if self.state == "new":
                    # We are going to ask user for an input
                    responseType = messages.ResponseElement.RESPONSE_TYPE_RESPONSE
                    cr = messages.createTextResponse(
                        canonicalMsg,
                        slotClass.prompt(),
                        responseType)
                    self.channelClient.sendResponse(cr)
                    self.state = "process_slot"
                    botState["slotClasses"] = slotClasses
                    return False

                # Finalize the slot
                elif self.state == "process_slot":
                    # We will evaluate the user's input

                    self.fillFrom(canonicalMsg, slotClasses, apiResult)
                    slotClass.validate()
                    self.state = "new"
                    botState["slotClasses"] = slotClasses
                    # continue to the next slot


        for slotClass in slotClasses:
            print(">>>>>>>>>>>>>>> slots; ", slotClass.name, slotClass.filled)
        # End slot filling
        # Now, all slots for this should be filled.
        # check
        allFilled = True
        for slotClass in slotClasses:
            if not slotClass.filled:
                allFilled = False
                break
        self.state = "new"
        print("all filled is : ", allFilled)
        return allFilled


    def handle(self, **kwargs):
        """ Support keyword intent, model intent and regex intent
        handling
        """
        canonicalMsg = kwargs.get("canonicalMsg")
        myraAPI = kwargs.get("myraAPI")

        # TODO(viksit): add regex and keyword intents for the less advanced uses.
        # If we got this far, then we need to run the model

        # local testing
        # ******************
        apiResult = myraAPI.get(canonicalMsg.text)
        intentStr = apiResult.intent.label
        intent_score = apiResult.intent.score


        """
        when an utterance comes in, we send it to our API to get an intent response back.
        once the intent is known, we determine whether it contains any slots.
        we then give this to the slot processor (its a list of slot items)
        the slot processor is the first thing that is run after we get the intent.
        once the slots are filled we should make them available as a dictionary locally.

        actionObject.slots = {
          "person": {
            "filled": false/true,
            "value": "foo",
            "entity_type": ENTITY_TYPE,
            "required": true/false,
            "validated": true/false
          }, ..
        }


        before we handle the intent, slots need to be filled.

        for slotclass in slotlist:
          channel.send(slotclass.prompt())
          slotValue = slotclass.get()
          v = slotclass.validate(slotValue)
          if v:
            continue
          else:
            ask again (max tries of 3)

        once we assert that all slots are filled, we run the process and give it slot information.

        """

        if self.state == "process_slot":
            # avoid using the intent itself.
            # continue the slot filling
            print("state is process_slot")
            slotClasses = botState.get("slotClasses")

            print("we're in user fill mode")
            allFilled = self.fill(slotClasses, canonicalMsg, apiResult)
            # once the slots are filled, we need to get into the intent process
            if allFilled is False:
                print("allFilled is false, so lets go back to the fill function")
                #allFilled = self.fill(slotClasses, canonicalMsg, apiResult)
                return

            # All slots are now filled
            intentStr = slotClasses[0].intent
            # state is now back to "new"

        if intentStr not in self.intentActions:
            raise ValueError("Intent '{}'' has not been registered".format(intentStr))

        # We have a valid intent.
        # Does it have slots?
        if intentStr not in self.intentSlots:
            return

        # TODO(viksit): serialize the intent-slot data structure
        slotClasses = self.intentSlots.get(intentStr)
        allFilled = self.fill(slotClasses, canonicalMsg, apiResult)
        if not allFilled:
            print("all slots were not filled")
            return

        # Get the actionObject
        actionObject = self.intentActions.get(intentStr)

        # Make slots available to actionObject
        # Make the apiResult available within the scope of the intent handler.
        import copy
        actionObject.slots = copy.deepcopy(slotClasses)
        actionObject.apiResult = apiResult
        actionObject.canonicalMsg = canonicalMsg
        actionObject.messages = messages
        actionObject.channelClient = self.channelClient
        # Once the actionObject is returned, lets clean out any state we have
        # Currently this doesn't actually return something.

        print("state: %s" % self.state)

        # Reset the slot state
        for slotClass in slotClasses:
            slotClass.reset()
        self.onetime = False

        return actionObject.process()


botState = {}


# Older
######################################################
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
        canonicalMsg = kwargs.get("canonicalMsg")
        myraAPI = kwargs.get("myraAPI")
        # TODO(viksit): Functionality
        # Check if any given string in keyword intents is in the input
        # If it is, run that function on the input.
        # You can match : equals, contains?

        # If we got this far, then we need to run the model
        apiResult = myraAPI.get(canonicalMsg.text)
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
                handlerFunction.func_globals['canonicalMsg'] = canonicalMsg
                return handlerFunction(self)
        else:
            raise ValueError("Intent '{}'' has not been registered".format(intentStr))


class BaseBot(object):

    # Constants
    REQUEST_STATE_NEW = "req-new"
    REQUEST_STATE_PROCESSED = "req-processed"

    # User profile keys
    UP_NAME = "up_name"

    def __init__(self, *args, **kwargs): # api, channel, ctxstore, config, actions, debug=False):
        self.api = kwargs.get("api")
        self.channelClient = kwargs.get("channelClient")
        self.ctxstore = kwargs.get("ctxstore")
        self.config = kwargs.get("config")
        self.debug = kwargs.get("debug")
        self.actions = kwargs.get("actions")
        # Add debug
        self.init()

    def init(self):
        # Override to initialize stuff in derived bots
        pass


    def createAndSendTextResponse(self, canonicalMsg, text, responseType=None):
        log.info("createAndSendTextResponse(%s)", locals())
        cr = messages.createTextResponse(canonicalMsg, text, responseType)
        log.info("cr: %s", cr)
        self.channelClient.sendResponse(cr)

    def errorResponse(self, canonicalMsg):
        self.createAndSendTextResponse(
            canonicalMsg, "Internal Error",
            messages.ResponseElement.RESPONSE_TYPE_RESPONSE)

    def process(self):
        pass





############ End library code ###########################

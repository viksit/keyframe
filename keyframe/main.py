from __future__ import print_function
import logging

import messages
import slot_fill
import copy

import uuid
from collections import defaultdict
import sys

log = logging.getLogger(__name__)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
logformat = "[%(levelname)1.1s %(asctime)s %(name)s] %(message)s"
formatter = logging.Formatter(logformat)
ch.setFormatter(formatter)
log.addHandler(ch)
log.setLevel(logging.DEBUG)
log.propagate = False


def getUUID():
   return str(uuid.uuid4()).replace("-", "")

botState = {}

# Class based decorators
class ActionObject(object):

   def __init__(self):
      self.__clsid__ = getUUID()
      self.apiResult = None
      self.canonicalMsg = None

   def process(self):
      pass

class BaseBotv2(object):


   def __init__(self, *args, **kwargs):

        self.api = kwargs.get("api")
        self.channelClient = kwargs.get("channelClient")
        self.ctxstore = kwargs.get("ctxstore")
        self.config = kwargs.get("config")
        self.debug = kwargs.get("debug")
        self.slotFill = slot_fill.SlotFill()
        self.slotFill.onetime = False

        self.intentActions = {}
        self.intentThresholds = {}
        self.keywordIntents = {}
        self.regexIntents = {}
        self.intentSlots = defaultdict(lambda: [])
        # Add debug
        self.init()

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
                #print("trying to fill slot %s from within sentence" % slotClass.name)
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
                        #print("\tslot was filled in this sentence")
                        continue
                    else:
                        #print("\tslot wasn't filled in this sentence")
                        # nothing was found
                        # we'll query the user for it.
                        pass
                else:
                    print("\tslot wasn't filled in this sentence")

    """
    Evaluate the given sentence to see which slots you can fill from it.
    Mark the ones that are filled
    The ones that remain unfilled are the ones that we come back to each time.
    """
    def fill(self, slotClasses, canonicalMsg, apiResult):


        #print("Availble slots: ")
        #for slotClass in slotClasses:
        #    print("\t slot, filled", slotClass.name, slotClass.filled)

        # First we should fill all possible slots from the sentence
        # For those that aren't filled, we run through this logic.

        #print("self onetime: ", self.onetime)
        if not self.onetime:
            self.fillFrom(canonicalMsg, slotClasses, apiResult)
            self.onetime = True

        # Now, whats left unfilled are slots that weren't completed by the user
        # in the first go. Ask the user for input here.
        print("++++++++++")
        for slotClass in slotClasses:
            # TODO(viksit): add validation step here as well.
            if not slotClass.filled:
                slotClass.canonicalMsg = canonicalMsg
                slotClass.apiResult = apiResult
                #print("trying to fill slot %s via user" % slotClass.name)
                #print("state: ", self.state)
                if self.state == "new":
                    # We are going to ask user for an input
                    responseType = messages.ResponseElement.RESPONSE_TYPE_RESPONSE
                    cr = messages.createTextResponse(
                        canonicalMsg,
                        slotClass.prompt(),
                        responseType)
                    # print(">>>>>> cr: ", cr)
                    # print(">>> channel client: ", self.channelClient)
                    # print(">>> self.cc: PRE", self.channelClient.responses)
                    self.channelClient.sendResponse(cr)
                    # print(">> self.cc POST responses: ", self.channelClient.responses)
                    self.state = "process_slot"
                    botState["slotClasses"] = slotClasses
                    return False

                # Finalize the slot
                elif self.state == "process_slot":
                    # We will evaluate the user's input

                    # TODO(viksit): this fillFrom function should refactor to slotClass.fill()
                    # This function could then be overwritten by a keyframe user

                    self.fillFrom(canonicalMsg, slotClasses, apiResult)
                    slotClass.validate()
                    self.state = "new"
                    botState["slotClasses"] = slotClasses
                    # continue to the next slot

        ######################################
        # End slot filling
        # Now, all slots for this should be filled.
        # check
        allFilled = True
        for slotClass in slotClasses:
            if not slotClass.filled:
                allFilled = False
                break
        self.state = "new"
        #print("all filled is : ", allFilled)
        return allFilled

    
    def handle(self, **kwargs):

        """
        Support keyword intent, model intent and regex intent
        handling
        """
        canonicalMsg = kwargs.get("canonicalMsg")
        myraAPI = kwargs.get("myraAPI")
        apiResult = myraAPI.get(canonicalMsg.text)
        intentStr = apiResult.intent.label

        # Resume a previously created slot fill loop.
        if self.slotFill.state == "process-slot":
            slotObjects = botState.get("slotObjects")
            allFilled = self.slotFill.fill(slotObjects, canonicalMsg, apiResult, botState, self.channelClient)
            if allFilled is False:
               return

        # We haven't yet start a slotfill and we may not have to.
        elif self.slotFill.state == "new":
            if intentStr not in self.intentActions:
                raise ValueError("Intent '{}'' has not been registered".format(intentStr))

            if intentStr in self.intentSlots:
                slotObjects = self.intentSlots.get(intentStr)
                allFilled = self.slotFill.fill(slotObjects, canonicalMsg, apiResult, botState, self.channelClient)
                if allFilled is False:
                    return
            else:
                # No slots need to be filled.
                pass

        # Get the actionObject
        actionObject = self.intentActions.get(intentStr)

        # TODO(viksit): invoke slot actions here in the future not before this
        # since the actions are what are connected to slots not the intent themselves.

        # Make slots available to actionObject
        # Make the apiResult available within the scope of the intent handler.
        # TODO(viksit): make slots a dict so it can be easily used by other people.
        actionObject.slots = copy.deepcopy(slotObjects)
        actionObject.apiResult = apiResult
        actionObject.canonicalMsg = canonicalMsg
        actionObject.messages = messages
        actionObject.channelClient = self.channelClient
        # Once the actionObject is returned, lets clean out any state we have
        # Currently this doesn't actually return something.

        print("state: %s" % self.slotFill.state)

        # Reset the slot state
        for slotObject in slotObjects:
           slotObject.reset()
        self.slotFill.onetime = False

        return actionObject.process()

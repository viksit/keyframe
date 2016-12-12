from __future__ import print_function
import sys
import logging

import messages
import misc
from six import add_metaclass
import re

log = logging.getLogger(__name__)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
logformat = "[%(levelname)1.1s %(asctime)s %(name)s] %(message)s"
formatter = logging.Formatter(logformat)
ch.setFormatter(formatter)
log.addHandler(ch)
log.setLevel(logging.DEBUG)
log.propagate = False

class Slot(object):

    parseOriginal = False
    parseResponse = False
    entityType = None
    required = False

    def __init__(self):
        self.name = re.sub(r"(.)([A-Z])", r"\1_\2", self.__class__.__name__).lower()
        self.filled = False
        self.value = None
        self.validated = False
        self.state = "new" # or process_slot

    def init(self, **kwargs):
        self.channelClient = kwargs.get("channelClient")

    def fill(self, canonicalMsg, apiResult, channelClient, parseOriginal=False, parseResponse=False):
        """
        if parseOriginal is true
          analyze the intent canonicalMsg to see if we can extract
          if extracted
            fill the slot
          else
            continue
        ask a question of the user, get response
        if parseResponse is True
          extract the entity from the response
        else
          take the whole response and fill the slot with it
        """
        self.apiResult = apiResult
        self.channelClient = channelClient
        self.canonicalMsg = canonicalMsg

        fillResult = None
        if self.state == "new":
            if parseOriginal is True:
                fillResult = self._extractSlotFromSentence()
                print("a: fillresult", fillResult)
                if fillResult:
                    self.value = fillResult
                    self.filled = True
                    return self.filled

            # The original sentence didn't have any items to fill this slot
            # Send a response
            responseType = messages.ResponseElement.RESPONSE_TYPE_RESPONSE
            cr = messages.createTextResponse(
                self.canonicalMsg,
                self.prompt(),
                responseType)
            channelClient.sendResponse(cr)
            self.state = "waiting-for-fill"

        # Waiting for user response
        elif self.state == "waiting-for-fill":
            # If we want the incoming response to be put through an entity extractor
            if parseResponse is True:
                fillResult = self._extractSlotFromSentence()
                if fillResult:
                    self.value = fillResult
                    self.filled = True
            # Otherwise we just take the whole utterance and incorporate it.
            else:
                fillResult = self.canonicalMsg.text
                self.value = fillResult
                self.filled = True
        return self.filled

    def _extractSlotFromSentence(self):
        res = None
        log.info("_extractSlotFromSentence: %s", self.name)
        e = self.apiResult.entities.entity_dict.get("builtin", {})

        # Entity type was found
        if self.entityType in e:
            # TODO(viksit): this needs to change to have "text" in all entities.
            k = "text"
            # TODO(viksit): special case for DATE. needs change in API.
            if self.entityType == "DATE":
                k = "date"

            # Extract the right value.
            tmp = [i.get(k) for i in e.get(self.entityType)]

            if len(tmp) > 0:
                log.info("\t(a) slot was filled in this sentence")
                res = tmp[0]
            else:
                log.info("\t(b) slot wasn't filled in this sentence")
        # The entity type wasnt found
        else:
            log.info("\t(c) slot wasn't filled in this sentence")

        # Return final result
        return res

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

# TODO(viksit): Make this go into the action object itself.
class SlotFill(object):

    def __init__(self):
        self.state = "new"

    def fill(self, slotObjects, canonicalMsg, apiResult, botState, channelClient):
        for slotObject in slotObjects:
            if not slotObject.filled:
                self.state = "process_slot"
                filled = slotObject.fill(canonicalMsg, apiResult, channelClient, parseOriginal=True, parseResponse=True)
                botState["slotObjects"] = slotObjects
                if filled is False:
                    return False
        # End slot filling
        # Now, all slots for this should be filled.
        allFilled = True
        for slotObject in slotObjects:
            if not slotObject.filled:
                allFilled = False
                break
        return allFilled

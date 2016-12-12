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


def getSlots(cls):
    allClasses = [cls.__getattribute__(cls, i) for i in cls.__dict__.keys() if i[:1] != '_']
    slotClasses = [i for i in allClasses if type(i) is type and issubclass(i, Slot)]
    return slotClasses

class Slot(object):

    SLOT_STATE_NEW = "new"
    SLOT_STATE_WAITING_FILL = "waiting_for_fill"

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

    def toJSONObject(self):
        return {
            "className": self.__class__.__name__,
            "name": self.name,
            "filled": self.filled,
            "value": self.value,
            "validated": self.validated,
            "state": self.state,
            "parseOriginal": self.parseOriginal,
            "parseResponse": self.parseResponse,
            "entityType": self.entityType,
            "required": self.required
        }

    def fromJSONObject(self, j):
        self.name = j.get("name")
        self.filled = j.get("filled")
        self.value = j.get("value")
        self.validated = j.get("validated")
        self.state = j.get("state")
        self.parseOriginal = j.get("parseOriginal")
        self.parseResponse = j.get("parseResponse")
        self.entityType = j.get("entityType")
        self.required = j.get("required")

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
        if self.state == Slot.SLOT_STATE_NEW:
            if parseOriginal is True:
                fillResult = self._extractSlotFromSentence()
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
            self.state = Slot.SLOT_STATE_WAITING_FILL

        # Waiting for user response
        elif self.state == Slot.SLOT_STATE_WAITING_FILL:
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

        ENTITY_BUILTIN = "builtin"
        ENTITY_DATE = "DATE"

        res = None
        log.info("_extractSlotFromSentence: %s", self.name)
        e = self.apiResult.entities.entity_dict.get(ENTITY_BUILTIN, {})

        # Entity type was found
        if self.entityType in e:
            # TODO(viksit): the Myra API needs to change to have "text" in all entities.
            k = "text"
            # TODO(viksit): special case for DATE. needs change in API.
            if self.entityType == ENTITY_DATE:
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

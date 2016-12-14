from __future__ import print_function
import sys
import logging
import inspect
import messages
import misc
from six import add_metaclass
import re
from dsl import BaseEntity

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

#@add_metaclass(misc.SlotMeta)
class Slot(object):

    SLOT_STATE_NEW = "new"
    SLOT_STATE_WAITING_FILL = "waiting_for_fill"


    def __init__(self):
        self.name = re.sub(r"(.)([A-Z])", r"\1_\2", self.__class__.__name__).lower()
        self.filled = False
        self.value = None
        self.validated = False
        self.state = Slot.SLOT_STATE_NEW
        self.parseOriginal = False
        self.parseResponse = False
        self.entityType = None
        self.required = False

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
            "entity": self.entity.toJSON(),
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
        self.entity = BaseEntity.fromJSON(j.get("entity"))
        self.required = j.get("required")

    def init(self, **kwargs):
        self.channelClient = kwargs.get("channelClient")

    def fill(self, canonicalMsg, apiResult, channelClient):
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

        # TODO(viksit): Make this cleaner
        if self.parseOriginal is True:
            assert self.apiResult is not None
        if self.parseResponse is True:
            assert self.apiResult is not None

        fillResult = None
        if self.state == Slot.SLOT_STATE_NEW:
            log.debug("(1) state: %s", self.state)
            log.debug("parseoriginal: %s", self.parseOriginal)
            if self.parseOriginal is True:
                fillResult = self._extractSlotFromSentence(canonicalMsg.text)
                log.debug("fillresult: %s", fillResult)
                if fillResult:
                    self.value = fillResult
                    self.filled = True
                    return self.filled

            # The original sentence didn't have any items to fill this slot
            # Send a response
            self._createAndSendResponse(self.prompt(), channelClient)
            self.state = Slot.SLOT_STATE_WAITING_FILL

        # Waiting for user response
        elif self.state == Slot.SLOT_STATE_WAITING_FILL:
            log.debug("(2) state: %s", self.state)
            # If we want the incoming response to be put through an entity extractor
            if self.parseResponse is True:
                log.debug("parse response is true")
                fillResult = self._extractSlotFromSentence(canonicalMsg)
                if fillResult:
                    self.value = fillResult
                    self.filled = True
                else:
                    # We notify the user that this value is invalid.
                    # ask to re-fill.
                    # currently this is an inifnite loop.
                    # TODO(viksit/nishant): add a nice way to control this.
                    msg = "You entered an incorrect value for %s. Please enter again." % self.name
                    self._createAndSendResponse(msg, channelClient)
                    self.state = Slot.SLOT_STATE_WAITING_FILL
                    self.filled = False
                    return self.filled
            # Otherwise we just take the whole utterance and incorporate it.
            else:
                fillResult = self.canonicalMsg.text
                self.value = fillResult
                self.filled = True
        return self.filled

    def _createAndSendResponse(self, msg, channelClient):
        responseType = messages.ResponseElement.RESPONSE_TYPE_RESPONSE
        cr = messages.createTextResponse(
            self.canonicalMsg,
            msg,
            responseType)
        channelClient.sendResponse(cr)

    def _extractSlotFromSentence(self, text):
        """
        Take a given sentence.
        For the current slot, run the entity_extract_fn() on it

        The return value of this is what we give to the result

        """

        res = None
        log.info("_extractSlotFromSentence: %s", self.name)
        assert self.apiResult is not None, "Failure in Myra API call"


        res = self.entity.entity_extract_fn(text=text)
        if res:
            log.info("(a) Slot was filled in this sentence")


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

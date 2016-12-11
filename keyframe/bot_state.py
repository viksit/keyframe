import messages
import channel_client
import fb
import config
import slot_fill
import copy
import bot_api

class BotState(object):

    """Serializable object for keeping bot state across requests.
    """

    def __init__(self):
        self._waiting = None
        # Json-compatible structure that allows
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

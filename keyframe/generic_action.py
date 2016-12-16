from __future__ import print_function
import logging

import messages
import slot_fill
import copy
import misc
import uuid
from collections import defaultdict
import sys

import constants
import actions
import generic_slot

from six import iteritems, add_metaclass


log = logging.getLogger(__name__)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
logformat = "[%(levelname)1.1s %(asctime)s %(name)s] %(message)s"
formatter = logging.Formatter(logformat)
ch.setFormatter(formatter)
log.addHandler(ch)
log.setLevel(logging.DEBUG)
log.propagate = False

class GenericActionObject(actions.ActionObject):

    def __init__(self, **kwargs):
        super(GenericActionObject, self).__init__(**kwargs)

    # I don't think we need all this complexity!
    def backup__init__(self, **kwargs):
        super(GenericActionObject, self).__init__(kwargs)
        self.specJson = kwargs.get("specJson")
        if not self.specJson:
            raise Exception(
                "Must initialize GenericActionObject with specJson")

    def getSlots(self):
        # TODO: Use self.specJson to get slots.
        # For now, hard-code slots here.
        return [
            generic_slot.GenericSlot,
            generic_slot.GenericSlot
            ]

    @classmethod
    def createActionObject(cls, specJson, intentStr, canonicalMsg, botState,
                           userProfile, requestState, api, channelClient,
                           actionObjectParams={}):
        # Create a GenericActionObject using specJson
        actionObject = cls()
        # TODO: Use specJson. Right now just hard-code.
        slotObjects = []
        ctr = 0
        runAPICall = False
        for slotClass in [GenericSlot, GenericSlot]:
            sc = slotClass()
            sc.entity = getattr(sc, "entity")
            sc.required = getattr(sc, "required")
            sc.parseOriginal = getattr(sc, "parseOriginal")
            sc.parseResponse = getattr(sc, "parseResponse")
            sc.promptMsg = "prompt_%s" % (ctr,)  # TODO: get from json
            slotObjects.append(sc)
            if sc.entity.needsAPICall:
                runAPICall = True

        actionObject.slotObjects = slotObjects
        
        if runAPICall:
            apiResult = api.get(canonicalMsg.text)
            actionObject.apiResult = apiResult

        actionObject.canonicalMsg = canonicalMsg
        actionObject.channelClient = channelClient
        actionObject.requestState = requestState
        actionObject.originalIntentStr = intentStr
        log.debug("createActionObject: %s", actionObject)
        return actionObject

        

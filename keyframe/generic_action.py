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
        self.msg = None

    def process(self):
        # TODO: put names from json config.
        msg = self.msg.format(**self.filledSlots)
        return self.respond(msg)

    def getSlots(self):
        raise Exception("This should not be used")

    @classmethod
    def createActionObject(cls, specJson, intentStr, canonicalMsg, botState,
                           userProfile, requestState, api, channelClient,
                           actionObjectParams={}):
        log.debug("createActionObject(%s)", locals())
        # Create a GenericActionObject using specJson
        actionObject = cls()
        # TODO: Use specJson. Right now just hard-code.
        actionObject.msg = specJson.get("text")
        assert actionObject.msg, "No text field in json: %s" % (specJson,)
        slots = specJson.get("slots", [])
        slotObjects = []
        runAPICall = False
        for slotSpec in slots:
            gc = generic_slot.GenericSlot()
            gc.entity = getattr(gc, "entity")
            gc.required = slotSpec.get("required")
            if not gc.required:
                log.debug("slotSpec does not specify required - getting default")
                gc.required = getattr(gc, "required")
            gc.parseOriginal = slotSpec.get("parse_original")
            if not gc.parseOriginal:
                log.debug("slotSpec does not specify parseOriginal - getting default")
                gc.parseOriginal = getattr(gc, "parseOriginal")
            gc.parseResponse = slotSpec.get("parse_response")
            if not gc.parseResponse:
                log.debug("slotSpec does not specify parseResponse - getting default")
                gc.parseResponse = getattr(gc, "parseResponse")
            gc.promptMsg = slotSpec.get("prompt")
            assert gc.promptMsg, "slot %s must have a prompt" % (slotSpec,)
            gc.name = slotSpec.get("name")
            assert gc.name, "slot %s must have a name" % (slotSpec,)
            slotObjects.append(gc)
            if gc.entity.needsAPICall:
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

        

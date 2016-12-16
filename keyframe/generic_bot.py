from __future__ import print_function
import logging

import messages
import slot_fill
import dsl
import copy
import misc
from collections import defaultdict
import sys
import utils

import keyframe.base
import keyframe.dsl
import keyframe.actions
import keyframe.generic_action

log = logging.getLogger(__name__)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
logformat = "[%(levelname)1.1s %(asctime)s %(name)s] %(message)s"
formatter = logging.Formatter(logformat)
ch.setFormatter(formatter)
log.addHandler(ch)
log.setLevel(logging.DEBUG)
log.propagate = False

class DefaultActionObject(keyframe.actions.ActionObject):
    def process(self):
        return self.respond("I did not understand what you said!")

class GenericBot(keyframe.base.BaseBot):

    # TODO: from json - hardcode for now for some basic test.
    def __init__(self, *args, **kwargs):
        super(GenericBot, self).__init__(*args, **kwargs)
        ki = keyframe.dsl.KeywordIntent(label="f1", keywords=["testing"])
        self.intentEvalSet.add(ki)
        di = keyframe.dsl.DefaultIntent()
        self.intentEvalSet.add(di)
        self.intentActions["f1"] = keyframe.generic_action.GenericActionObject
        self.intentActions["default"] = DefaultActionObject()
        log.debug("GenericBot.__init__() called")

    def createActionObject(self, actionObjectCls, intentStr,
                           canonicalMsg, botState,
                           userProfile, requestState):
        log.debug("GenericBot.createActionObject(%s) called", locals())
        if actionObjectCls == keyframe.generic_action.GenericActionObject:
            log.debug("creating GenericActionObject")
            return actionObjectCls.createActionObject(
                {}, # This is the json spec - currently just a placeholder
                intentStr, canonicalMsg, botState,
                userProfile, requestState, self.api, self.channelClient)

        return actionObjectCls.createActionObject(
            intentStr, canonicalMsg, botState,
            userProfile, requestState, self.api, self.channelClient)


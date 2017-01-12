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

    def __init__(self, *args, **kwargs):
        super(GenericBot, self).__init__(*args, **kwargs)
        self.specJson = kwargs.get("configJson")
        self.agentId = kwargs.get("agentId")
        self.accountId = kwargs.get("accountId")

        log.debug("self.specJson: %s", self.specJson)
        self.configFromJson()

    def _botStateKey(self, userId, channel):
        """
        A generic bot has an account Id and an agentId associated with it.
        """

        k = "botstate.{classname}.{botname}.{accountId}.{agentId}.{userId}.{channel}".format(**{
            "classname": self.__class__.__name__,
            "botname": self.name,
            "accountId": self.accountId,
            "agentId": self.agentId,
            "userId": userId,
            "channel": channel
        })
        return k

    def configFromJson(self):
        log.debug("GenericBot.configFromJson()")
        intents = self.specJson.get("intents")
        for (intentId, intentProperties) in intents.iteritems():
            intentType = intentProperties.get("intent_type")
            if intentType == "api":
                i = keyframe.dsl.APIIntent(label=intentId)
                self.intentEvalSet.add(i)
                self.intentActions[intentId] = keyframe.generic_action.GenericActionObject
            elif intentType == "keyword":
                intentKeywords = intentProperties.get("intent_data")
                assert intentKeywords, "keywords intent must have keywords"
                assert isinstance(intentKeywords, list), "keywords intent must have a list of keywords"
                i = keyframe.dsl.KeywordIntent(
                    label=intentId,
                    keywords=intentKeywords)
                self.intentEvalSet.add(i)
                self.intentActions[intentId] = keyframe.generic_action.GenericActionObject
            elif intentType == "default":
                i = keyframe.dsl.DefaultIntent(label="default")
                self.intentEvalSet.add(i)
                self.intentActions[intentId] = keyframe.generic_action.GenericActionObject
            else:
                raise Exception("Unknown intentType: %s" % (intentType,))

    def createActionObject(self, actionObjectCls, intentStr,
                           canonicalMsg, botState,
                           userProfile, requestState,
                           apiResult=None, newIntent=None):
        log.debug("GenericBot.createActionObject(%s) called", locals())
        if actionObjectCls == keyframe.generic_action.GenericActionObject:
            actionObjectSpecJson = self.specJson.get(
                "intents", {}).get(intentStr)
            log.debug("creating GenericActionObject with json: %s",
                      actionObjectSpecJson)
            return actionObjectCls.createActionObject(
                actionObjectSpecJson,
                intentStr, canonicalMsg, botState,
                userProfile, requestState, self.api, self.channelClient,
                apiResult=apiResult, newIntent=newIntent)
        return actionObjectCls.createActionObject(
            intentStr, canonicalMsg, botState,
            userProfile, requestState, self.api, self.channelClient,
            apiResult=apiResult, newIntent=newIntent)

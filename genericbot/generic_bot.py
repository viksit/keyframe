from __future__ import print_function

from __future__ import absolute_import
import copy
from collections import defaultdict
import sys
import re

import logging

import keyframe.base
import keyframe.dsl
import keyframe.actions
from . import generic_action

log = logging.getLogger(__name__)

class DefaultActionObject(keyframe.actions.ActionObject):
    def process(self):
        return self.respond("I did not understand what you said!")

class GenericBot(keyframe.base.BaseBot):

    def __init__(self, *args, **kwargs):
        super(GenericBot, self).__init__(*args, **kwargs)
        self.specJson = kwargs.get("configJson")
        self.agentId = kwargs.get("agentId")
        self.accountId = kwargs.get("accountId")

        #log.debug("self.specJson: %s", self.specJson)
        self.configFromJson()

    def _botStateKey(self, userId, channel, instanceId):
        """
        A generic bot has an account Id and an agentId associated with it.
        """

        k = "botstate.{classname}.{botname}.{accountId}.{agentId}.{userId}.{channel}.{instanceId}".format(**{
            "classname": self.__class__.__name__,
            "botname": self.name,
            "accountId": self.accountId,
            "agentId": self.agentId,
            "userId": userId,
            "channel": channel,
            "instanceId":instanceId
        })
        log.debug("GenericBot: returning botstate key: %s", k)
        return k

    def configFromJson(self):
        log.debug("GenericBot.configFromJson()")
        # Nothing else to do here.

    def getStartTopic(self):
        x = self.specJson.get("start_topic")
        assert x, "Bot spec must have a start topic"
        return x

    def createActionObject(self, accountId, agentId,
                           topicId,
                           canonicalMsg, botState,
                           userProfile, requestState,
                           apiResult=None, newTopic=None, topicNodeId=None,
                           config=None):
        log.info("createActionObject called")
        log.debug("GenericBot.createActionObject(%s) called", locals())
        actionObjectSpecJson = self.specJson.get(
            "topics", {}).get(topicId)
        assert actionObjectSpecJson, "No spec for topicId: %s" % (topicId,)
        #log.debug("creating GenericActionObject with json: %s",
        #          actionObjectSpecJson)
        return generic_action.GenericActionObject.createActionObject(
            accountId, agentId,
            actionObjectSpecJson, topicId,
            canonicalMsg, botState,
            userProfile, requestState, self.api, self.channelClient,
            apiResult=apiResult, newTopic=newTopic,
            intentModelParams=self.specJson.get("intent_model_params"),
            topicNodeId=topicNodeId, config=config,
            agentParams=self.specJson.get("params"))

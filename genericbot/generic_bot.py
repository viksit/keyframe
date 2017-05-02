from __future__ import print_function

import copy
from collections import defaultdict
import sys

import logging

import keyframe.base
import keyframe.dsl
import keyframe.actions
import generic_action

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
        log.debug("GenericBot: returning botstate key: %s", k)
        return k

    def configFromJson(self):
        log.debug("GenericBot.configFromJson()")
        # Nothing else to do here.

    def getStartTopic(self):
        x = self.specJson.get("start_topic")
        assert x, "Bot spec must have a start topic"
        return x

    def getStartActionObjectJsonXXX(self):
        startActionObjectName = self.specJson.get("start_topic")
        assert startActionObjectName, "Bot spec must have start_topic"
        startActionObjectJson = self.specJson.get("topics", {}).get(
            startActionObjectName)
        assert startActionObjectJson, "Bot spec does not have topic: %s" % (
            startActionObjectName,)
        return startActionObjectJson

    def createActionObject(self, topicId,
                           canonicalMsg, botState,
                           userProfile, requestState,
                           apiResult=None, newTopic=None):
        log.debug("GenericBot.createActionObject(%s) called", locals())
        actionObjectSpecJson = self.specJson.get(
            "topics", {}).get(topicId)
        #log.debug("creating GenericActionObject with json: %s",
        #          actionObjectSpecJson)
        return generic_action.GenericActionObject.createActionObject(
            actionObjectSpecJson, topicId,
            canonicalMsg, botState,
            userProfile, requestState, self.api, self.channelClient,
            apiResult=apiResult, newTopic=newTopic)

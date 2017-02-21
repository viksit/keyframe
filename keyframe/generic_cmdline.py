from __future__ import print_function
import sys, os
from os.path import expanduser, join
from flask import Flask, request, Response
from flask import Flask, current_app, jsonify, make_response
import yaml
import json
import traceback
import logging

from pymyra.api import client

from keyframe.cmdline import BotCmdLineHandler
from keyframe import channel_client
from keyframe import messages
from keyframe import config
from keyframe import generic_bot
from keyframe import bot_stores

log = logging.getLogger(__name__)

# Deployment for command line
class GenericCmdlineHandler(BotCmdLineHandler):

    def getChannelClient(self, cf):
        return channel_client.getChannelClient(
            channel=messages.CHANNEL_CMDLINE,
            requestType=None,
            config=cf)

    def init(self):
        log.debug("GenericCmdlineHandler.init")
        # channel configuration
        cf = config.getConfig()
        self.channelClient = self.getChannelClient(cf)
        self.kvStore = self.kwargs.get("kvStore")
        assert self.kvStore, "kvStore is required"
        self.cfg = self.kwargs.get("cfg")
        assert self.cfg, "config is required"

        accountId = self.kwargs.get("accountId")
        accountSecret = self.kwargs.get("accountSecret")
        configJson = self.kwargs.get("config_json")
        bms = bot_stores.BotMetaStore(kvStore=self.kvStore)
        if not len(configJson.keys()):
            agentId = self.kwargs.get("agentId")
            configJson = bms.getJsonSpec(accountId, agentId)

        cj = configJson.get("config_json")
        intentModelId = cj.get("intent_model_id")
        modelParams = cj.get("params")

        # TODO: inject json and have the GenericBot decipher it!!
        api = None
        log.debug("GOT intent_model_id: %s, modelParams: %s",
                  intentModelId, modelParams)
        if intentModelId:
            apicfg = {
                "account_id": accountId,
                "account_secret": accountSecret,
                "hostname": self.cfg.MYRA_API_HOSTNAME
            }
            api = client.connect(apicfg)
            api.set_intent_model(intentModelId)
            api.set_params(modelParams)
        self.bot = generic_bot.GenericBot(
            kvStore=self.kvStore, configJson=configJson.get("config_json"), api=api)
        self.bot.setChannelClient(self.channelClient)


""" Example script.
< botcmd clear state
> {}
< I got robbed
> {"intentStr":"accident_security", "responseType":"transitionmsg"}
> {"intentStr":"accident_security", "responseType":"slotfill"}
< 6507665785
> {"intentStr":"accident_security", "responseType":"response"}
< thanks
> {"intentStr":"concierge.prebuilt.greeting.thanks", "responseType":"response"}
"""

"""
Example of how to run the test:
(keyframe1) ~/work/keyframe/tutorial/genericbot $ rlwrap python gbot.py script db 3rxCO9rydbBIf3DOMb9lFh 4b94f2de6d6554a006099c963e586d47485f9b4d e7704006fc5542acb04e3522fa64f53a /Users/nishant/tmp/scripts/2 > /tmp/out 2> /tmp/err; echo $?
0
(keyframe1) ~/work/keyframe/tutorial/genericbot $ cat /tmp/out
[OK] lengths: actual: 1, expected: 1
[OK] lengths: actual: 2, expected: 2
[OK] responseType: actual:transitionmsg, expected:transitionmsg
[OK] intentStr: actual:accident_security, expected:accident_security
[OK] responseType: actual:slotfill, expected:slotfill
[OK] intentStr: actual:accident_security, expected:accident_security
[OK] lengths: actual: 1, expected: 1
[OK] responseType: actual:response, expected:response
[OK] intentStr: actual:accident_security, expected:accident_security
[OK] lengths: actual: 1, expected: 1
[OK] responseType: actual:response, expected:response
[OK] intentStr: actual:concierge.prebuilt.greeting.thanks, expected:concierge.prebuilt.greeting.thanks

"""
class ScriptHandler(GenericCmdlineHandler):
    def getChannelClient(self, cf):
        return channel_client.getChannelClient(
            channel=messages.CHANNEL_SCRIPT,
            requestType=None,
            config=cf)

    def scriptFile(self, scriptFile):
        self.scriptFile = scriptFile
        self.script = self.createScript(scriptFile)

    def processMessage(self, userInput):
       canonicalMsg = messages.CanonicalMsg(
           channel=messages.CHANNEL_SCRIPT,
           httpType=None,
           userId=self.userId,
           text=userInput)
       self.bot.process(canonicalMsg)

    def _st(self, x, y, errors):
        if x == y:
            return "OK"
        else:
            errors[0] += 1
            return "ERROR"

    def executeScript(self):
        log.debug("executeScript called")
        script = self.script
        num_errors = [0]
        for d in script:
            log.debug("D: %s", d)
            if "input" in d:
                self.processMessage(d["input"])
            log.debug("PROCESS MESSAGE: %s" % (d["input"],))
            _actual = self.channelClient.popResponses()
            actual = []
            for canonicalResponse in _actual:
                actual.extend(canonicalResponse.responseElements)
            log.debug("actual: %s" % (actual,))

            log.debug("expected: %s" % (d.get("expected"),))
            st = self._st(len(actual), len(d.get("expected")), num_errors)
            print("[%s] lengths: actual: %s, expected: %s" % (
                st,
                len(actual), len(d.get("expected"))))
            for (a, e) in zip(actual, d.get("expected")):
                if e.get("responseType"):
                    st = self._st(a.responseType, e.get("responseType"), num_errors)
                    print("[%s] responseType: actual:%s, expected:%s" % (
                        st,
                        a.responseType, e.get("responseType")))
                if e.get("intentStr"):
                    st = self._st(a.responseMeta.intentStr, e.get("intentStr"), num_errors)
                    print("[%s] intentStr: actual:%s, expected:%s" % (
                        st,
                        a.responseMeta.intentStr, e.get("intentStr")))
                if e.get("text"):
                    st = self._st(a.text, e.get("text"), num_errors)
                    print("[%s] text: actual:%s, expected:%s" % (
                        st,
                        a.text, e.get("text")))
                    
        return num_errors[0]
        
    @classmethod
    def createScript(cls, scriptFile):
        assert scriptFile and os.path.isfile(scriptFile)
        script = []
        sl = None
        with open(scriptFile, "r") as f:
            sl = f.readlines()
        scriptLines = []
        for l in sl:
            if l.startswith("#") or l.startswith("@"):
                continue
            if not l.strip():
                continue
            scriptLines.append(l.strip())
        script = []
        ctr = 0
        while True:
            if ctr >= len(scriptLines):
                break
            l = scriptLines[ctr]
            log.info("l: %s", l)
            if l.startswith("<"):
                # input to bot
                input = l[1:].strip()
                expected = []
                i = 1
                while ctr + i < len(scriptLines):
                    nl = scriptLines[ctr + i]
                    log.debug("nl: %s", nl)
                    if nl.startswith(">"):
                        expected.append(json.loads(nl[1:].strip()))
                        i += 1
                    else:
                        break
                ctr += i
                log.debug("ctr: %s", ctr)
                script.append({"input":input, "expected":expected})
            else:
                assert False, "unexpected input from file"
        return script

    def getChannelClient(self, cf):
        return channel_client.getChannelClient(
            channel=messages.CHANNEL_SCRIPT,
            requestType=None,
            config=cf)



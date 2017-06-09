from __future__ import print_function

#import readline
import inspect
import logging
import urlparse

import messages
import channel_client
import fb
import config
import slot_fill
import copy

import uuid
from collections import defaultdict
import sys

log = logging.getLogger(__name__)
#log.setLevel(10)

class CmdLineHandler(object):

    def __init__(self, **kwargs):
        self.userId = kwargs.get("userId")
        if not self.userId:
            self.userId = "bot_arch_msghandler_user"
        self.kwargs = kwargs
        self.init()

    def init(self):
        # Override to initialize other MessageHandler variables.
        pass

    def begin(self):
        while True:
            try:
                userInput = raw_input("> ")
                if not userInput:
                    continue
                isCmd = self.checkCmds(userInput)
                if isCmd:
                    continue
                self.processMessage(userInput)
            except (KeyboardInterrupt, EOFError, SystemExit):
                break

    # Handle incoming messages and return the response
    def processMessage(self, userInput):
        raise NotImplementedError()

    def checkCmds(self, userInput):
        if userInput.startswith("/user_id"):
            if len(userInput.split()) == 2:
                self.userId = userInput.split()[1]
                print("user_id set to: %s" % (self.userId,))
            else:
                print("usage: /user_id <user-id>")
            return True
        return False


class BotCmdLineHandler(CmdLineHandler):

    def init(self):
       self.bot = None  # Create your bot here by overriding init in your class.
       raise NotImplementedError()

    def processMessage(self, userInput):
        log.debug("processMessage(%s)", locals())
        text = userInput
        botStateUid = None
        if userInput.strip().startswith(">"):
            # Treat at url parameters
            x = urlparse.parse_qs(userInput[1:].strip())
            text = x.get("text",[None])[0]
            botStateUid = x.get("bot_state_uid",[None])[0]
            log.debug("extracted url params: text=%s, botStateUid=%s",
                      text, botStateUid)
        canonicalMsg = messages.CanonicalMsg(
            channel=messages.CHANNEL_CMDLINE,
            httpType=None,
            userId=self.userId,
            text=text,
            botStateUid=botStateUid)
        log.debug("canonicalMsg: %s", canonicalMsg)
        self.bot.process(canonicalMsg)

from __future__ import print_function
import inspect
import logging

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
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
logformat = "[%(levelname)1.1s %(asctime)s %(name)s] %(message)s"
formatter = logging.Formatter(logformat)
ch.setFormatter(formatter)
log.addHandler(ch)
log.setLevel(logging.DEBUG)
log.propagate = False


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
       canonicalMsg = messages.CanonicalMsg(
           channel=messages.CHANNEL_CMDLINE,
           httpType=None,
           userId=self.userId,
           text=userInput)
       self.bot.process(canonicalMsg)

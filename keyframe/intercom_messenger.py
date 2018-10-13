#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
import sys, os
from os.path import expanduser, join
#from flask import Flask, request, Response
#from flask import Flask, current_app, jsonify, make_response
#from flask_cors import CORS, cross_origin
import datetime

from functools import wraps
import yaml
import json
import traceback
import base64
import logging
from six.moves import range


#import pymyra.api.inference_proxy_client as inference_proxy_client
#import pymyra.api.inference_proxy_api as inference_proxy_api

#from keyframe.cmdline import BotCmdLineHandler
#from keyframe.base import BaseBot
#from keyframe.actions import ActionObject
#from keyframe.slot_fill import Slot
#from keyframe.bot_api import BotAPI
#from keyframe import channel_client

#from keyframe import messages
#from keyframe import config
#from keyframe import store_api
#from keyframe import bot_stores
#import keyframe.event_api as event_api
#import keyframe.utils
#import keyframe.widget_target

import keyframe.imlib as imlib


#logging.basicConfig()
log = logging.getLogger("keyframe.gbot.intercom_messenger")
#rootLog = logging.getLogger()
#rootLog.setLevel(logging.INFO)




"""
CONFIGURE URL
https://myra-dev.ngrok.io/v2/intercom/configure

SUBMIT URL
https://myra-dev.ngrok.io/v2/intercom/submit

INITIALIZE URL
https://myra-dev.ngrok.io/v2/intercom/initialize

SUBMIT SHEET URL
https://myra-dev.ngrok.io/v2/intercom/submit_sheet

"""

def _pprint(data):
    log.info(json.dumps(data, indent=2))

def getTextCanvas(text):
    c = imlib.Canvas(
        content = imlib.Content(
            components = [
                imlib.TextComponent(
                    id="bot_text_response",
                    text=text
                )
            ]
        )
    )
    return imlib.makeResponse(c)

def getSampleAppCanvas():
    c = imlib.Canvas(
        content = imlib.Content(
            components = [
                imlib.InputComponent(
                    id="user_question",  # This exact text is important for now.
                    label="Whats your question?",
                    placeholder="I can't configure my dns ...",
                    value="",
                    action=imlib.SubmitAction()
                )
            ]
        )
    )
    return imlib.makeResponse(c)

def getConfigureCanvas():
    c = imlib.Canvas(
        content=imlib.Content(
            components=[
                imlib.InputComponent(
                    id="user_myra_config",
                    label="Enter your myra configuration ID",
                    placeholder="something ID",
                    value="",
                    action=imlib.SubmitAction()
                )
            ]
        ))
    return imlib.makeResponse(c)


def getSearchResultsCanvas():
    l = imlib.ListComponent(items=[])
    num_items = 4
    for i in range(0, num_items):
        l.items.append(imlib.ListItemComponent(
            id="article_id_{}".format(i),
            title="some title {}".format(i),
            subtitle="some subtitle for {}".format(i),
            action=imlib.SubmitAction()
        ))
    c = imlib.Canvas(
        content=imlib.Content(
            components=[
                l,
                imlib.DividerComponent(),
                imlib.ButtonComponent(
                    id="button-back",
                    label="back",
                    style="secondary",
                    action=imlib.SubmitAction()
                ),
                imlib.ButtonComponent(
                    id="button2",
                    label="open link",
                    style="primary",
                    action=imlib.URLAction(url="www.google.com")
                ),
                imlib.ButtonComponent(
                    id="button3",
                    label="yes",
                    style="primary",
                    action=imlib.SubmitAction()
                )

            ]
        ))
    return imlib.makeResponse(c)

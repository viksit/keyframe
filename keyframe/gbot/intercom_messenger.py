#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
import sys, os
from os.path import expanduser, join
from flask import Flask, request, Response
from flask import Flask, current_app, jsonify, make_response
from flask_cors import CORS, cross_origin
import datetime

from functools import wraps
import yaml
import json
import traceback
import base64
import logging
from six.moves import range


import pymyra.api.inference_proxy_client as inference_proxy_client
import pymyra.api.inference_proxy_api as inference_proxy_api

from keyframe.cmdline import BotCmdLineHandler
from keyframe.base import BaseBot
from keyframe.actions import ActionObject
from keyframe.slot_fill import Slot
from keyframe.bot_api import BotAPI
from keyframe import channel_client

from keyframe import messages
from keyframe import config
from keyframe import store_api
from keyframe import bot_stores
import keyframe.event_api as event_api
import keyframe.utils
import keyframe.widget_target

import keyframe.gbot.imlib as imlib


logging.basicConfig()
log = logging.getLogger("keyframe.gbot.intercom_messenger")
rootLog = logging.getLogger()
rootLog.setLevel(logging.INFO)




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
    print(json.dumps(data, indent=2))

def getSampleInput():
    res = {
        "type": "input",
        "id": "user_myra_config",
        "label": "Enter your myra configuration ID",
        "placeholder": "abc13fsdfff",
        "value": "",
        "action": {
            "type": "submit"
        }
    }
    return res


def getSampleApp():
    res = {
        "type": "input",
        "id": "user_question",
        "label": "Whats your question?",
        "placeholder": "I cant configure my DNS what should I do?",
        "value": "",
        "action": {
            "type": "submit"
        }
    }
    return res

def _getSampleApp():
    res = imlib.InputComponent(
        id = "user_question",
        label = "Whats your question?",
        placeholder = "I can't configure my dns ...",
        value = "",
        action = imlib.SubmitAction()
    )
    return imlib.asdict(res)



def getSampleListResponse():
    res = {
        "type": "list",
        "items": [
            {
                "type": "item",
                "id": "article-123b",
                "title": "How to install the messenger",
                "subtitle": "An article explaining how to integrate Intercom",
                "action": {
                    "type": "submit"
                }
            },
            {
                "type": "item",
                "id": "article-123a",
                "title": "How to install the messenger",
                "subtitle": "An article explaining how to integrate Intercom",
                "action": {
                    "type": "submit"
                }
            },
            {
                "type": "item",
                "id": "article-123c",
                "title": "How to install the messenger",
                "subtitle": "An article explaining how to integrate Intercom",
                "action": {
                    "type": "submit"
                }
            },
            {
                "type": "item",
                "id": "article-123d",
                "title": "How to install the messenger",
                "subtitle": "An article explaining how to integrate Intercom",
                "action": {
                    "type": "submit"
                }
            }
        ]
    }
    return res

def _getSampleListResponse():
    res = imlib.ListComponent(items=[])
    num_items = 4
    for i in range(0, num_items):
        res.items.append(imlib.ListItemComponent(
            id="article_id_{}".format(i),
            title="some title {}".format(i),
            subtitle="some subtitle for {}".format(i),
            action=imlib.SubmitAction()
        ))
    return imlib.asdict(res)

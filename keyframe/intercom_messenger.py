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

def getDividerComponent():
    c = imlib.DividerComponent()
    return imlib.asdict(c)

def getSpacerComponent(size="l"):
    c = imlib.SpacerComponent(size=size)
    return imlib.asdict(c)

def getSheetComponent():
    pass

def getTextComponent(text, id=None):
    if not id:
        id = "myra_text_component"
    c = imlib.TextComponent(
        id=id,
        text=text,
        style="header",
        align="left")
    ret = imlib.asdict(c)
    log.debug(ret)
    return ret

def getSingleSelectComponent(label, values, id=None):
    # For now, do not allow value to be specified.
    if not id:
        id = "myra_singleselect_component"
    options = []
    ctr = 0
    for v in values:
        o = imlib.SingleSelectOptionComponent(
            id="option_%s" % (ctr,),
            text=v)
        options.append(o)
        ctr += 1
    c = imlib.SingleSelectComponent(
        id=id,
        label=label,
        options=options,
        action=imlib.SubmitAction())
    ret = imlib.asdict(c)
    log.debug(ret)
    return ret

def getButtonComponent(values, style="primary", id=None, actions={}):
    # actions = {value1:action1,...}
    buttons = []
    ctr = 0
    for v in values:
        action = imlib.SubmitAction()
        action = actions.get(v, action)
        o = imlib.ButtonComponent(
            id="button_%s" % (ctr,),
            label=v,
            style=style,
            action=action)
        buttons.append(imlib.asdict(o))
        ctr += 1
    log.debug(buttons)
    return buttons

def getTextInputComponent(label, id=None, placeholder=None, value=None):
    if not id:
        id = "myra_textinput_component"
    c = imlib.InputComponent(
        id=id,
        label=label,
        placeholder=placeholder,
        value=value,
        action=imlib.SubmitAction())
    ret = imlib.asdict(c)
    log.debug(ret)
    return ret

def getListComponent(listItems):
    l = imlib.ListComponent(items=[])
    d = {}
    ctr = 0
    for i in listItems:
        action = None
        t = i.get("type")
        if t == "workflow":
            action = imlib.SubmitAction()
        elif t == "kb":
            action = imlib.URLAction(url=i.get("url"))
        else:
            raise Exception("Unknown type: %s", t)
        id = f"listitem_{ctr}"
        l.items.append(imlib.ListItemComponent(
            id=id,
            title=i.get("title"),
            action=action))
        d[id] = {"workflowid":i.get("workflowid")}
        ctr += 1
    ret = imlib.asdict(l)
    log.debug(ret)
    return {"component":ret, "stored_data":d}

def getInputFromAppRequest(appResponse):
    """Extract the text input from the response.
    """
    componentId = appResponse.get("component_id")
    v = appResponse.get("input_values", {}).get(componentId)
    if v:
        return v
    canvasComponents = appResponse.get("current_canvas", {}).get("content", {}).get("components")
    for c in canvasComponents:
        if componentId == c.get("id"):
            return c.get("label")
    v = appResponse.get("current_canvas", {}).get("stored_data", {}).get(componentId)
    if v:
        return v
    raise Exception("could not extract user input as text from request.")



# ----------------
def getTextCanvas(text):
    c = imlib.Canvas(
        content = imlib.Content(
            components = [
                imlib.TextComponent(
                    id="bot_text_response",
                    text=text,
                    style="header",
                    align="left"
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

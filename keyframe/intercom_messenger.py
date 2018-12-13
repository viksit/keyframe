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
from six import string_types

from functools import wraps
import yaml
import json
import traceback
import base64
import logging
from six.moves import range
import urllib

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
import keyframe.utils as utils

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

# Move below to files.
WIDGET_WEBPAGE_SEARCH = """
<html>
    <head>
        <script src="https://js.intercomcdn.com/messenger-sheet-library.latest.js"></script>
    </head>
    <body>
        <button id="hiddenctabutton" type="submit" style="display:none;"/>
        <input type="text" value="%(user_question)s" id="userquestion">
        <script>
         window.MyraConciergeSettings = {
             container: 'concierge-widget',
             accountId: '%(account_id)s',
             agentId: '%(agent_id)s',
             realm: '%(realm)s',
             widgetVersion: '%(widget_version)s',
             firstLoad: true,
             customProps: {"testing-key1":"testing-value1"},  // it seems from empirical testing that this is important for the good and proper functioning of the widget.
             position: 'myra-right',
             ctaElement: '#hiddenctabutton',
             firstMessageElement: '#userquestion',
             popupByDefault: true
         };
        </script>
        <script>
         (function() {
             var w = window;
             var mcs = w.MyraConciergeSettings;
             var d = document;
             function l() {
                 var s = d.createElement('script');
                 s.type = 'text/javascript';
                 s.src = '//cdn-%(realm)s.myralabs.com/widget/v3/widget.selfserve.js';
                 s.onload = function() {
                     window.MyraConcierge('init', window.MyraConciergeSettings);
                 };
                 var x = d.getElementsByTagName('script')[0];
                 x.parentNode.insertBefore(s, x);
             }
             if (w.attachEvent) {
                 w.attachEvent('onload', l);
             } else {
                 w.addEventListener('load', l, false);
             }
             l();
         })();
        </script>
    </body>
</html>
"""

WIDGET_WEBPAGE_WELCOME = """
<html>
    <head>
        <script src="https://js.intercomcdn.com/messenger-sheet-library.latest.js"></script>
    </head>
    <body>
        <button id="hiddenctabutton" type="submit" style="display:none;"/>
        <script>
         window.MyraConciergeSettings = {
             container: 'concierge-widget',
             accountId: '%(account_id)s',
             agentId: '%(agent_id)s',
             realm: '%(realm)s',
             widgetVersion: '%(widget_version)s',
             firstLoad: true,
             customProps: {"testing-key1":"testing-value1"},  // it seems from empirical testing that this is important for the good and proper functioning of the widget.
             position: 'myra-right',
             ctaElement: '#hiddenctabutton',
             popupByDefault: true
         };
        </script>
        <script>
         (function() {
             var w = window;
             var mcs = w.MyraConciergeSettings;
             var d = document;
             function l() {
                 var s = d.createElement('script');
                 s.type = 'text/javascript';
                 s.src = '//cdn-%(realm)s.myralabs.com/widget/v3/widget.selfserve.js';
                 s.onload = function() {
                     window.MyraConcierge('init', window.MyraConciergeSettings);
                 };
                 var x = d.getElementsByTagName('script')[0];
                 x.parentNode.insertBefore(s, x);
             }
             if (w.attachEvent) {
                 w.attachEvent('onload', l);
             } else {
                 w.addEventListener('load', l, false);
             }
             l();
         })();
        </script>
    </body>
</html>
"""


def _pprint(data):
    log.info(json.dumps(data, indent=2))

def getDividerComponent():
    c = imlib.DividerComponent()
    return imlib.asdict(c)

def getSpacerComponent(size="l"):
    c = imlib.SpacerComponent(size=size)
    return imlib.asdict(c)

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
    # Also, intercom does not allow more than 11 elements, so enforce that here.
    if not id:
        id = "myra_singleselect_component"
    options = []
    ctr = 0
    for v in values:
        o = imlib.SingleSelectOptionComponent(
            id="option_%s" % (utils.getUUID(),),
            text=v)
        options.append(o)
        ctr += 1
        if ctr >= 11:
            break
    c = imlib.SingleSelectComponent(
        id=id,
        label=label,
        options=options,
        action=imlib.SubmitAction())
    ret = imlib.asdict(c)
    log.debug(ret)
    return ret

def getButtonComponent(values, style="primary", id=None):
    buttons = []
    ctr = 0
    for v in values:
        o = imlib.ButtonComponent(
            id="button_%s" % (ctr,),
            label=v,
            style=style,
            action=imlib.SubmitAction())
        buttons.append(imlib.asdict(o))
        ctr += 1
    log.debug(buttons)
    return buttons

def getTextInputComponent(label, id=None, placeholder="", value=""):
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
            subtitle=i.get("snippet"),
            action=action))
        d[id] = {"workflowid":i.get("workflowid")}
        ctr += 1
    ret = imlib.asdict(l)
    log.debug(ret)
    return {"component":ret, "stored_data":d}

def getInputFromAppRequestSingleText(appResponse, textInputId):
    d = appResponse.get("input_values")
    if not d:
        return None
    return d.get(textInputId)

def getInputFromAppRequestForWidgetPage(appResponse, pinConfig):
    """Get input from the form submit for the widget.
    """
    log.info("getInputFromAppRequestForwidgetpage(%s)", locals())
    componentId = appResponse.get("component_id")
    if componentId == "button-widget":
        d = appResponse.get("input_values")
        if not d:
            return None
        return d.get("user_question")
    elif componentId.startswith("button-pin-workflow"):
        # This is a pinned item.
        try:
            i = int(componentId.split("-")[-1])
            pinItem = pinConfig[i]
            p = pinItem.get("payload")
            log.info("returning input: %s", p)
            return p
        except:
            log.exception("could not get selected pinned item")
            raise

    raise Exception("unrecognized componentId: %s" % (componentId,))


def getInputFromAppRequest(appResponse):
    """Extract the text input from the response.
    """
    componentId = appResponse.get("component_id")
    if not componentId or componentId == "button-start":
        return "[topic=default]"
    v = appResponse.get("input_values", {}).get(componentId)
    if v and (not componentId or not componentId.startswith("myra_singleselect")):
        return v
    canvasComponents = appResponse.get("current_canvas", {}).get("content", {}).get("components")
    if not canvasComponents:
        return "[topic=default]"
    for c in canvasComponents:
        if componentId == c.get("id"):
            if componentId.startswith("myra_singleselect"):
                for o in c.get("options"):
                    if o.get("id") == v:
                        return o.get("text")
                raise Exception("Could not extract value from singleselect")
            else:
                return c.get("label")
    v = appResponse.get("current_canvas", {}).get("stored_data", {}).get(componentId)
    if v:
        if isinstance(v, string_types):
            return v
        elif isinstance(v, dict):
            if "workflowid" in v:
                return v["workflowid"]
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

def getLiveCanvas(requestUrl):
    parts = urllib.parse.urlparse(requestUrl)
    initUrl = urllib.parse.urlunparse(
        #(parts[0], parts[1], "/v2/intercom/startinit", "", "", "")
        ("https", parts[1], "/v2/intercom/startinit", "", "", "")
    )
    c = imlib.LiveCanvas(
        content_url = initUrl
    )

    return imlib.makeResponse(c)

def getStartInitCanvasWithOptions(action1=None, action2=None, widgetUrl=None):
    if not action1:
        action1 = imlib.SubmitAction()
    if not action2 and widgetUrl:
        action2 = imlib.SheetsAction(url=widgetUrl)
    c = imlib.Canvas(
        content = imlib.Content(
            components = [
                imlib.TextComponent(
                    id="bot_text_msg",
                    text="Click on the buttons below to ask a question.",
                    style="header",
                    align="left"
                ),
                imlib.ButtonComponent(
                    id="button-app",
                    label="Use the native app to ask a question",
                    style="primary",
                    action=action1
                ),
                imlib.ButtonComponent(
                    id="button-widget",
                    label="Use the inapp widget to ask a question",
                    style="primary",
                    action=action2
                )
            ]
        )
    )
    return imlib.makeResponse(c)

def getStartInitCanvas(widgetUrl, userMsg=None):
    if not userMsg:
        userMsg = ("I am a virtual assistant. I can help answer your questions faster."
                   " What is your question?")
    action = imlib.SheetsAction(url=widgetUrl)
    c = imlib.Canvas(
        content = imlib.Content(
            components = [
                imlib.TextComponent(
                    id="bot_text_msg",
                    text=userMsg,
                    style="header",
                    align="left"
                ),
                imlib.InputComponent(
                    id="user_question",
                    label="Question",
                    placeholder="",
                    value=""
                    #action=imlib.SubmitAction()
                ),
                imlib.ButtonComponent(
                    id="button-widget",
                    label="Submit",
                    style="primary",
                    action=action
                )
            ]
        )
    )
    return imlib.makeResponse(c)

def getStartInitCanvasWithPinnedItems(widgetUrl, pinnedItems, userMsg=None):
    if not userMsg:
        userMsg = ("I am a virtual assistant. I can help answer your questions faster."
                   " Click if your question is below or ask me by typing in the textbox.")
    action = imlib.SheetsAction(url=widgetUrl)
    components = [
        imlib.TextComponent(
            id="bot_text_msg",
            text=userMsg,
            style="header",
            align="left"
        )]

    for i, pi in enumerate(pinnedItems):
        if pi.get("type") in ("document"):
            log.info("drop pinned item type: %s", pi.get("type"))
            continue
        components.append(
            imlib.ButtonComponent(
                id="button-pin-%s-%i" % (pi.get("type"), i),
                label=pi.get("label"),
                style="primary",
                action=action
            )
        )

    components.extend([
        imlib.InputComponent(
            id="user_question",
            label="Question",
            placeholder="",
            value=""
            #action=imlib.SubmitAction()
        ),
        imlib.ButtonComponent(
            id="button-widget",
            label="Submit",
            style="primary",
            action=action
        )
    ])
    c = imlib.Canvas(
        content = imlib.Content(components = components),
        stored_data = {"stored_data_key1": "stored_data_value1"})

    return imlib.makeResponse(c)


def getSampleAppCanvas():
    c = imlib.Canvas(
        content = imlib.Content(
            components = [
                imlib.InputComponent(
                    id="user_question",  # This exact text is important for now.
                    label="Whats your questionasdf,asjflsak fjlaskfn alsdfkn?",
                    placeholder="I can't configure my dns ...",
                    value="",
                    action=imlib.SubmitAction()
                )
            ]
        )
    )
    return imlib.makeResponse(c)

def getConfigureCanvas(msg):
    c = imlib.Canvas(
        content=imlib.Content(
            components=[
                imlib.TextComponent(
                    id="myra_config_msg",
                    text=msg,
                    style="header",
                    align="left"
                ),
                imlib.InputComponent(
                    id="account_id",
                    label="Myra Account Id",
                    placeholder="Account Id",
                    value=""
                    #action=imlib.SubmitAction()
                ),
                # imlib.InputComponent(
                #     id="account_secret",
                #     label="Myra Account Secret",
                #     placeholder="Account Secret",
                #     value=""
                #     #action=imlib.SubmitAction()
                # ),
                imlib.ButtonComponent(
                    id="button_config_submit",
                    label="Submit",
                    style="primary",
                    action=imlib.SubmitAction()
                )
            ]
        ))
    return imlib.makeResponse(c)


def getNoInstallCanvas():
    c = imlib.Canvas(
        content=imlib.Content(
            components=[
                imlib.TextComponent(
                    id="myra_config_msg",
                    text="Your Myra account does not exist or is not active. Please have an active Myra account and then try again.",
                    style="header",
                    align="left"
                ),
                imlib.ButtonComponent(
                    id="button_install_cancel",
                    label="OK",
                    style="primary",
                    action=imlib.SubmitAction()
                )
            ]
        ))
    return imlib.makeResponse(c)

def getInstallOkCancelCanvas(msg):
    c = imlib.Canvas(
        content=imlib.Content(
            components=[
                imlib.TextComponent(
                    id="myra_config_msg",
                    text="Your Myra account is ready to deploy. Confirm?",
                    style="header",
                    align="left"
                ),
                imlib.ButtonComponent(
                    id="button_install_ok",
                    label="OK",
                    style="primary",
                    action=imlib.SubmitAction()
                ),
                imlib.ButtonComponent(
                    id="button_install_cancel",
                    label="Cancel",
                    style="primary",
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

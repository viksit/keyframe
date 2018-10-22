from __future__ import absolute_import

import os
import sys
import time
import json
import time
import logging

from functools import wraps
import traceback
import tempfile
import requests

from flask import Flask, request, session, render_template, jsonify, redirect, url_for, send_from_directory, jsonify, Response, make_response, send_file

# Uses keyframe libraries.
import keyframe.intercom_messenger as kim
import keyframe.imlib as imlib

log = logging.getLogger(__name__)

SHEET2_HTML = '''
<html>
    <body>

        <h3> Test myra widget integration</h3>
        <script>
         window.MyraConciergeSettings = {
             container: 'concierge-widget',
             
             // prod agent for convflow demo
             accountId: '3rxCO9rydbBIf3DOMb9lFh',  // nishant+dev@myralabs.com  
             //accountId: 'bd80e4cbc57f47178ef323b87fd4823d',  // demo+dev@myralabs.com
             //agentId: '8d5c4d5d319647e19d3d41d97a4069de',
             //agentId: '10d2e63e2888481286de037258cb0bc9',  // digitalocean-dev-1-20180815
             // agentId: 'c6f3611f06c949b7a22bbe188d1a805b',  // wpengine_v3-dev-3 (nishant+dev)
             agentId: '3c1b9fd4341c4be09a8e8a0172cff06a',  // nishant-intercom-app-search-1
             // agentId: 'default',
             // agentId: '98a43a145a6b4164bdd81f0065d21a60',  // wpengine-demo
             realm: 'dev',
             //accountId: '7BbmKJgxsMKRuAcBjNA1Zo',
             //agentId: '259f09c9603a4743bcbbd22cc7f9dc42', 
             //realm: 'dev',
             widgetVersion: 'v2',
             //firstLoad: true,
             customProps: {"testing-key1":"testing-value1"},
             position: 'myra-right'
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
                 s.async = true;
                 //s.src = '//ml-static-dev.s3-website-us-west-2.amazonaws.com/widget/v3/widget.wpengine.js';
                 //s.src = '//ml-static-dev.s3-website-us-west-2.amazonaws.com/widget/v3/widget.c1234.js';
                 s.src = '//ml-static-dev.s3-website-us-west-2.amazonaws.com/widget/v3/widget.dashboard.js';
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
         })();
        </script>
    </body>
</html>

'''

SHEET1_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>myra-widget</title>
</head>
<body>
  <div style="height: 200px; background-color: silver;" id="bigdiv">
      <h4>TEST</h4>
  </div>

</body>
<script>
    window.MyraConciergeSettings = {
    container: 'concierge-widget',
    firstLoad: true,
    //accountId: 'bd80e4cbc57f47178ef323b87fd4823d', // demo+dev
    // agentId: '5e3192a91c3e4398ab30c5afe9224685', //  wpengine-dev-20180927
    realm: 'dev',

    // wpengine workflow go live agent dev
    accountId: 'bd80e4cbc57f47178ef323b87fd4823d',
    agentId: 'dcc91d404f92488bb4e5a3f6c6404ff4',

    //   agentId: 'f111cef48e1548be8d121f9649b368eb',
    //   accountId: '3oPxV9oFXxzHYxuvpy56a9',
    //   realm: 'dev',
    //position:"myra-left",
   //widgetVersion: 'v3',
   pageElementProps: {
   },
   customProps: {
   }
 };
 (function(d, s, id, url){
      var js, ijs = d.getElementsByTagName(s)[0];
      if (d.getElementById(id)){ return; }
      js = d.createElement(s); js.id = id; js.async = 1;
      js.onload = function(){window.MyraConcierge('init', window.MyraConciergeSettings);};
      js.src = url + "main.js";ijs.parentNode.insertBefore(js, ijs);
    }(document, 'script', 'myrawidget',''));
</script>
</html>
'''

app = Flask(__name__)

@app.route("/v2/intercom/sheet1", methods=["GET","POST"])
def sheet1():
    return SHEET1_HTML

@app.route("/v2/intercom/sheet2", methods=["GET","POST"])
def sheet2():
    return SHEET2_HTML

@app.route("/v2/intercom/configure", methods=["GET", "POST"])
def configure():
    print_request_details()
    return Response(), 200

@app.route("/v2/intercom/initialize", methods=["GET", "POST"])
def initialize():
    print_request_details()
    return Response(), 200

@app.route("/v2/intercom/submit", methods=["GET", "POST"])
def submit():
    print_request_details()
    e = request.json
    #id = e.get("input_values", {}).get("component_id_input")
    id = kim.getInputFromAppRequest(e)
    log.info("extracted input: %s", id)
    components = []
    stored_data = None
    if not id:
        id = "component_id_input"
    r = get_components(id)
    _c = r.get("components")
    log.info("_c: %s", _c)
    if isinstance(_c, list):
        components.extend(_c)
    else:
        components.append(_c)
    log.info("components: %s", components)
    canvasDict = {"canvas":
            {"content":
             {"version":"0.1",
              "components":components}}}
    if "stored_data" in r:
        canvasDict["canvas"]["stored_data"] = r["stored_data"]
    log.info("canvasDict: %s", canvasDict)
    return jsonify(canvasDict)

def get_components(id):
    log.info("get_component(%s)", locals())
    components = []
    storedData = {}
    if id == "singleselect":
        c = kim.getSingleSelectComponent(
            label="example of a single select component",
            values=["text", "textinput", "singleselect", "button", "list"])
        components.append(c)
    elif id == "component_id_input":
        c = kim.getButtonComponent(
            #label="Choose component to display",
            values=["text", "textinput", "singleselect", "button", "list", "sheet"],
            style="primary",
            #actions={"sheet":imlib.SheetsAction(url="https://myra-dev.ngrok.io/v2/intercom/sheet2")}
            actions={"sheet":imlib.SheetsAction(url="http://myra-misc2.ngrok.io/web/test.html")}
        )
        components.extend(c)
    elif id == "component_id_input_old":
        c = kim.getTextInputComponent(
            label="Input id of component to see",
            id=id)
        components.append(c)
    elif id == "text":
        c = kim.getTextComponent(
            text="example of a text component")
        components.append(c)
        components.append(kim.getSpacerComponent())
        c = kim.getDividerComponent()
        components.append(c)
        components.append(kim.getSpacerComponent())
        c = get_components("component_id_input").get("components")
        components.extend(c)
    elif id == "textinput":
        c = kim.getTextInputComponent(
            label="label for text input component",
            placeholder="placeholder for text input",
            value="this is the default value")
        components.append(c)
    elif id == "button":
        c = kim.getButtonComponent(
            #label="label for button component",
            values=["button0", "button1"],
            style="primary")
        components.extend(c)
    elif id == "list":
        l = [{"url":"https://www.google.com", "title":"go to google", "type":"kb"},
             {"type":"workflow", "title":"this is a workflow", "workflowid":"[transfer-topic=topic_2833383uesdjsdisdfsf]"}]
        r = kim.getListComponent(l)
        components.append(r.get("component"))
        storedData = r.get("stored_data")
    else:
        c = get_components("component_id_input").get("components")
        components.extend(c)

    log.info("returning components: %s", components)
    return {"components":components, "stored_data":storedData}


def print_request_details(**kwargs):
    #print("DICT: %s" % (request.__dict__,))
    #print("\nDATA: %s" % (request.data,))
    #print("\n\nFORM: %s" % (request.form,))
    #print("\n\nrequest.url: %s" % (request.url,))
    if request.json:
        print("\n\nrequest.json: (%s) %s" % (
            type(request.json), request.json))
    print("kwargs: %s" % (kwargs,))


if __name__ == "__main__":
    logging.basicConfig()
    _l = logging.getLogger()
    _l.setLevel(20)
    log.setLevel(10)
    port = 5000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    app.run(debug=True, host="0.0.0.0", port=port)



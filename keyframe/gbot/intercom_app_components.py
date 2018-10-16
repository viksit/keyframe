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

log = logging.getLogger(__name__)

app = Flask(__name__)

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
    id = e.get("input_values", {}).get("component_id_input")
    components = []
    if id:
        _c = get_component(id)
        if isinstance(_c, list):
            components.extend(_c)
        else:
            components.append(_c)
    _c = get_component("component_id_input")
    components.append(_c)
    canvasDict = {"canvas":
            {"content":
             {"version":"0.1",
              "components":components}}}
    log.info("canvasDict: %s", canvasDict)
    return jsonify(canvasDict)

def get_component(id):
    log.info("get_component(%s)", locals())
    c = None
    if id == "singleselect":
        c = kim.getSingleSelectComponent(
            label="example of a single select component",
            values=["option0", "option1"])
    elif id == "component_id_input":
        c = kim.getTextInputComponent(
            label="Input id of component to see",
            id=id)
    elif id == "text":
        c = kim.getTextComponent(
            text="example of a text component")
    elif id == "textinput":
        c = kim.getTextInputComponent(
            label="label for text input component",
            placeholder="placeholder for text input",
            value="this is the default value")
    elif id == "button":
        c = kim.getButtonComponent(
            label="label for button component",
            values=["button0", "button1"],
            style="primary")
    else:
        raise NotImplementedError()
    log.info("returning component: %s", c)
    return c


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

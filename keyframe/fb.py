import os
import logging
import copy
import requests
import json

log = logging.getLogger(__name__)

"""
Example of an FB message:
{"object":"page","entry":[{"id":"580994445412762","time":1469659220169,"messaging":[{"sender":{"id":"129978077421100"},"recipient":{"id":"580994445412762"},"timestamp":1469659220133,"message":{"mid":"mid.1469659220123:a46d1f3576c306b773","seq":91,"text":"hello"}}]}]}

Example of a basic text response:
{
  "recipient":{
    "id":"129978077421100"
  },
  "message":{
    "text":"facebook API response"
  }
}

Example of a horizontal scrollable carousel:
{
  "recipient":{
    "id":"129978077421100"
  },
  "message":{
    "attachment":{
      "type":"template",
      "payload":{
        "template_type":"generic",
        "elements":[
          {
            "title":"Welcome to Peter\'s Hats",
            "image_url":"http://petersapparel.parseapp.com/img/item100-thumb.png",
            "subtitle":"We\'ve got the right hat for everyone.",
            "buttons":[
              {
                "type":"web_url",
                "url":"https://petersapparel.parseapp.com/view_item?item_id=100",
                "title":"View Website"
              },
              {
                "type":"postback",
                "title":"Start Chatting",
                "payload":"USER_DEFINED_PAYLOAD"
              }
            ]
          },
          {
            "title":"Girl Power: Hello Giggles Launches With Lady-Friendly Comedy",
            "image_url":"http://s1.r29static.com//bin/entry/195/50x/52638/image.jpg",
            "subtitle":"Girl Power",
            "buttons":[
              {
                "type":"web_url",
                "url":"http://www.refinery29.com/hello-giggles-website-launches-in-l-a",
                "title":"View Website"
              },
              {
                "type":"postback",
                "title":"Start Chatting",
                "payload":"USER_DEFINED_PAYLOAD"
              }
            ]
          }
        ]
      }
    }
  }
}

"""

# Utility to handle Facebook GET verification of webhook.
# Facebook calls the webhook like this:
# http://webhook?hub.challenge=<token>&hub.mode=<...>&hub.verify_token=<fb_page_access_token>
# If the webhook is a Gateway API, use a velocity template to get all the queryparams
# from the call to the lambda function.
# template: api_gateway_velocity_template.txt
#
# Webhook must respond with 200 and return back <token>
# The utility below does this, as well as checking the page_access_token
# if it is given. Call it from your lambda_handler.

def gateway_webhook_verify_handler(
        event, context, page_access_token=None):
    log.info("event: %s" % (event,))
    log.info("context: %s" % (context,))
    qs = event.get("params",{}).get("querystring")
    log.info("qs: %s", qs)
    if not qs:
        log.error("unknown message format")
        return
    return return_challenge(qs, page_access_token)

def return_challenge(params, page_access_token=None):
    ret_token = params.get("hub.challenge")
    log.info("ret_token: %s", ret_token)
    if not ret_token:
        return None
    ret_token = int(ret_token)
    #if page_access_token and params.get("hub.verify_token"):
    #    if params.get("hub.verify_token") == page_access_token:
    #        return ret_token
    #    else:
    #        return None
    return ret_token


DEBUG_NO_SEND = os.getenv("DEBUG_NO_SEND", "false")

_session = requests.Session()
_session.headers.update({"Content-Type": "application/json"})

def _extract(fb_msg):
    log.info("FB_MSG: %s", fb_msg)
    if fb_msg.get("object") != "page":
        log.info("fb_msg are not handled - returning")
        return None
    entry = fb_msg.get("entry", [])
    if not entry:
        log.warn("unexpected message format - returning")
        return None
    messaging = entry[0].get("messaging")
    if not messaging:
        log.warn("unexpected messaging format - returning")
        return None
    return messaging[-1]

def extract(fb_msg):
    _msg = _extract(fb_msg)
    if not _msg:
        return None
    sender_id = _msg.get("sender",{}).get("id")
    message = _msg.get("message")
    text = None
    #text = _msg.get("message",{}).get("text")
    if message:
        text = message.get("text")
    else:
        postback = _msg.get("postback")
        if postback:
            text = postback.get("payload")

    if not sender_id or not text:
        return None
    return (sender_id, text)

def response_text(sender_id, text_msg):
    return {"recipient":{"id":sender_id},
            "message":{"text":text_msg[:310]}}  # FB limitation

def response_yesnobutton(sender_id, text_msg):
    x = {
        "recipient":{
            "id":sender_id
        },
        "message":{
            "attachment":{
                "type":"template",
                "payload":{
                    "template_type":"button",
                    "text":text_msg,
                    "buttons":[
                        {
                            "type":"postback",
                            "title":"Yes",
                            "payload":"yes"
                        },
                        {
                            "type":"postback",
                            "title":"No",
                            "payload":"no"
                        }
                    ]
                }
            }
        }
    }
    return x


def response_carousel(sender_id, response):
    elements = []
    response_dict = {
        "recipient":{"id":sender_id},
        "message":{
            "attachment":{
                "type":"template",
                "payload":{
                    "template_type":"generic",
                    "elements":elements
                }
            }
        }
    }
    LENGTH_LIMIT = 2000
    for r in response:
        x = json.dumps(response_dict)
        currentLength = len(x)
        if currentLength > LENGTH_LIMIT:
            log.info("currentLength: %s, breaking", currentLength)
            break
        if not r.get("image_url"):
            continue

        element = {
            "title":r.get("title"),
            "image_url":r.get("image_url"),
            "buttons":[
                {"type":"web_url",
                 "url":r.get("url"),
                 "title":"View Website"}
            ]
        }
        elementLength = len(json.dumps(element))
        if currentLength + elementLength > LENGTH_LIMIT:
            log.info("newLength: %s, breaking",
                     currentLength + elementLength)
            break
        log.info("adding element to elements")
        elements.append(element)
    return response_dict

def copy_replace(fb_msg, msg_text):
    fb_msg_copy = copy.deepcopy(fb_msg)
    _msg = _extract(fb_msg_copy)
    if not _msg:
        return None
    _msg_d = _msg.get("message")
    _msg_d["text"] = msg_text
    return fb_msg_copy

class FBSendException(Exception):
    pass

def send(response_dict, fb_page_access_token):
    data = json.dumps(response_dict)
    log.info("data: %s", data)
    url = "https://graph.facebook.com/v2.6/me/messages?access_token=%s" % (
        fb_page_access_token,)
    log.info("url: %s", url)
    log.info("data (%s): %s", len(data), data)
    if DEBUG_NO_SEND == "true":
        log.info("DATA: %s", data)
        return
    r = _session.post(url, data=data)
    log.info("r: %s", r.status_code)
    if r.status_code != 200:
        log.error("%s", r.__dict__)
        raise FBSendException(r.status_code)


def get_user_name(fb_id, fb_page_access_token):
    url = "https://graph.facebook.com/v2.7/%(fb_id)s?access_token=%(fb_page_access_token)s&debug=all&fields=first_name,last_name&format=json&method=get&pretty=0&suppress_http_code=1" % locals()
    r = _session.get(url)
    log.info("r: %s, %s", r.status_code, r.json())
    return (r.json().get("first_name"), r.json().get("last_name"))

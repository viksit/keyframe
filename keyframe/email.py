from __future__ import absolute_import
import requests
from . import config
import traceback
import logging

log = logging.getLogger(__name__)
log.warn("IMPORTING KEYFRAME.EMAIL")

cfg = config.Config()

def safe_send(toAddr, subject, body):
    try:
        return send(toAddr, subject, body)
    except:
        traceback.print_exc()
        return False

def send(toAddr, subject, body):
    log.debug("email.send(%s)", locals())
    if not cfg.SEND_EMAIL:
        return True
    r = requests.post(
        "https://api.mailgun.net/v3/sandbox29b89d1732e442debccaee5ef096abf4.mailgun.org/messages",
        auth=("api", cfg.SEND_EMAIL_AUTH_KEY),
        data={"from": "Mailgun Sandbox <postmaster@sandbox29b89d1732e442debccaee5ef096abf4.mailgun.org>",
              "to": toAddr,
              "subject": subject,
              "text": body})
    log.debug("r.status_code: %s, r.text: %s", r.status_code, r.text)
    return r.ok

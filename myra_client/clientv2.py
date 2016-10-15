from __future__ import print_function
import os, sys
import requests
import json
import logging

try:
    import http.client as http_client
except ImportError:
    # Python 2
    import httplib as http_client

from myra_client import utils

# Logging and debug utilities

http_client.HTTPConnection.debuglevel = 0
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

def set_debug():
    http_client.HTTPConnection.debuglevel = 1
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True
    log.setLevel(logging.DEBUG)

# Package level functions

def get_config(config_file=None):
    return utils.MyraConfig(config_file)

def connect(config, debug=False):

    assert type(config) == utils.MyraConfig
    if debug:
        set_debug()

    api_config = config.get("api")
    hostname = api_config.get("hostname")
    version = api_config.get("version")
    user_config = config.get("user")
    account_id = user_config.get("account_id")
    account_secret = user_config.get("account_secret")
    return InferenceClient(account_id = account_id,
                           account_secret = account_secret,
                           myra_api_server = hostname,
                           myra_api_version = version)

class InferenceClientError(Exception):
    pass

class IntentResult(object):
    def __init__(self, label, score):
        self.label = label
        self.score = score

class EntityResult(object):
    def __init__(self, entities):
        self.entities = entities


class InferenceResult(object):

    def __init__(self, intent_label=None, intent_score=None, entities=None):
        self.intent = IntentResult(intent_label, intent_score)
        self.entities = EntityResult(entities)


class InferenceClient(object):
    def __init__(
            self,
            account_id, account_secret,
            intent_model_id=None, entity_model_id=None,
            myra_api_server=None, myra_api_version=None):

        self.account_id = account_id
        self.account_secret = account_secret
        self.intent_model_id = intent_model_id
        self.entity_model_id = entity_model_id

        if myra_api_server:
            self.hostname = myra_api_server
        else:
            self.hostname = os.getenv(
                "MYRA_API_SERVER", "api.myralabs.com")

        if myra_api_version:
            self.api_version = myra_api_version
        else:
            self.api_version = os.getenv(
                "MYRA_INFERENCE_VERSION", "v2")

        self._session = requests.Session()
        self._session.headers.update(self._get_headers())

    def _get_headers(self):
        return {
            "X-ACCOUNT-ID": self.account_id,
            "X-ACCOUNT-SECRET": self.account_secret
        }

    def _get(self, text, intent_model_id, entity_model_id):
        url = "http://%s/api/%s/parse?text=%s" % (
            self.hostname, self.api_version, text)
        if intent_model_id:
            url += "&intent_model_id=%s" % (intent_model_id,)
        if entity_model_id:
            url += "&entity_model_id=%s" % (entity_model_id,)
        log.debug("url: %s", url)
        r = self._session.get(url)
        if r.status_code != 200:
            print(r.__dict__)
            raise InferenceClientError(
                "Error: status_code %s" % (r.status_code,))
        log.debug("r.json: %s", r.json())
        return r.json()

    def _get_dict(self, text, intent_model_id, entity_model_id):
        js = self._get(text, intent_model_id, entity_model_id)
        log.debug(">>> js: %s", js)
        return js

    def _extract_intent(self, response_dict):
        """d: dict representing returned json
        """
        i = response_dict.get("result",{}).get("intents",{})
        status_code = i.get("status",{}).get("status_code")
        if not status_code or status_code != 200:
            return None
        d = i.get("user_defined",{})
        intent = d.get("intent")
        score = d.get("score")
        return (intent, score)

    def _extract_entities(self, response_dict):
        i = response_dict.get("result", {}).get("entities")
        status_code = i.get("status",{}).get("status_code")
        if status_code and status_code != 200:
            return None
        return i

    # Public API

    def set_intent_model(self, intent_model_id):
        self.intent_model_id = intent_model_id

    def set_entity_model(self, entity_model_id):
        self.entity_model_id = entity_model_id

    def get_intent(self, text, intent_model_id=None):
        if not intent_model_id:
            intent_model_id = self.intent_model_id
        d = self._get_dict(text, intent_model_id, None)
        (intent, score) = self._extract_intent(d)
        return IntentResult(intent, score)

    def get_entities(self, text, entity_model_id=None):
        if not entity_model_id:
            entity_model_id = self.entity_model_id
        d = self._get_dict(text, None, entity_model_id)
        e = self._extract_entities(d)
        return EntityResult(e)

    def get(self, text, intent_model_id=None, entity_model_id=None):
        if not entity_model_id:
            entity_model_id = self.entity_model_id
        if not intent_model_id:
            intent_model_id = self.intent_model_id
        d = self._get_dict(text, intent_model_id, entity_model_id)
        (intent, score) = self._extract_intent(d)

        entities = self._extract_entities(d)
        print(">>>>>>", entities)
        return InferenceResult(intent, score, entities)


def main():
    account_id = os.getenv("MYRA_ACCOUNT_ID")

    if not account_id:
        print((sys.stderr, "environment must have MYRA_ACCOUNT_ID"))
        sys.exit(1)
    account_secret = os.getenv("MYRA_ACCOUNT_SECRET")

    if not account_secret:
        print((sys.stderr, "environment must have MYRA_ACCOUNT_SECRET"))
        sys.exit(1)

    if not len(sys.argv) == 2:
        print((sys.stderr, "usage: client.py <msg>"))
        sys.exit(1)

    msg = sys.argv[1]
    intent_model_id = os.getenv("MYRA_INTENT_MODEL_ID")
    entity_model_id = os.getenv("MYRA_ENTITY_MODEL_ID")

    if not intent_model_id and not entity_model_id:
        print((sys.stderr, "environment must have MYRA_ENTITY_MODEL_ID and/or MYRA_INTENT_MODEL_ID"))
        sys.exit(1)

    ic = InferenceClient(
        account_id=account_id,
        account_secret=account_secret,
        intent_model_id=intent_model_id,
        entity_model_id=entity_model_id)

    if intent_model_id:
        intent = ic.get_intent(msg)
        print(("intent: %s" % (intent,)))

    if entity_model_id:
        entity = ic.get_entities(msg)
        print(("entity: %s" % (entity,)))


if __name__ == "__main__":
    main()

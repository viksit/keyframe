import os, sys
import requests
import json
import logging

log = logging.getLogger(__name__)

class InferenceClientError(Exception):
    pass

class InferenceClient(object):
    def __init__(
            self, account_id, account_secret,
            intent_model_id=None, entity_model_id=None):
        self.account_id = account_id
        self.account_secret = account_secret
        self.intent_model_id = intent_model_id
        self.entity_model_id = entity_model_id
        self.hostname = os.getenv(
            "MYRA_INFERENCE_SERVER", "api.myralabs.com")
        self.api_version = os.getenv(
            "MYRA_INFERENCE_VERSION", "v2")
        self._session = requests.Session()
        self._session.headers.update(self._getHeaders())

    def _getHeaders(self):
        return {"X-ACCOUNT-ID": self.account_id,
                "X-ACCOUNT-SECRET": self.account_secret}

    def _get(self, text, intent_model_id, entity_model_id):
        # May need to change this to also get the model_type
        # because the parse call may have intent/entity_model_id
        url = "http://%s/api/%s/parse?text=%s" % (
            self.hostname, self.api_version, text)
        if intent_model_id:
            url += "&intent_model_id=%s" % (intent_model_id,)
        if entity_model_id:
            url += "&entity_model_id=%s" % (entity_model_id,)
        log.info("url: %s", url)
        r = self._session.get(url)
        if r.status_code != 200:
            raise InferenceClientError(
                "status_code %s" % (r.status_code,))
        log.info("r.text: %s", r.text)
        return r.text

    def _getDict(self, text, intent_model_id, entity_model_id):
        js = self._get(text, intent_model_id, entity_model_id)
        log.debug("js: %s", js)
        return json.loads(js)

    def _extractIntent(self, response_dict):
        '''d: dict representing returned json
        '''
        i = response_dict.get("result",{}).get("intent",{})
        status_code = i.get("status",{}).get("status_code")
        if not status_code or status_code != 200:
            return None
        d = i.get("data",{})
        intent = d.get("intent")
        score = d.get("score")
        return (intent, score)

    def _extractEntities(self, response_dict):
        i = response_dict.get("result",{}).get("entity")
        status_code = i.get("status",{}).get("status_code")
        if not status_code or status_code != 200:
            return None
        d = i.get("data",{})
        return d

    def getIntent(self, text, intent_model_id=None):
        if not intent_model_id:
            intent_model_id = self.intent_model_id
        d = self._getDict(text, intent_model_id, None)
        (intent, score) = self._extractIntent(d)
        return (intent, score)

    def getEntities(self, text, entity_model_id=None):
        # TODO: Extract the right entities from the api data
        # and return that vs all of the data as now.
        if not entity_model_id:
            entity_model_id = self.entity_model_id
        d = self._getDict(text, None, entity_model_id)
        return self._extractEntities(d)


def main():
    account_id = os.getenv("MYRA_ACCOUNT_ID")
    if not account_id:
        print >> sys.stderr, "environment must have MYRA_ACCOUNT_ID"
        sys.exit(1)
    account_secret = os.getenv("MYRA_ACCOUNT_SECRET")
    if not account_secret:
        print >> sys.stderr, "environment must have MYRA_ACCOUNT_SECRET"
        sys.exit(1)
    if not len(sys.argv) == 2:
        print >> sys.stderr, "usage: client.py <msg>"
        sys.exit(1)
    msg = sys.argv[1]
    intent_model_id = os.getenv("MYRA_INTENT_MODEL_ID")
    entity_model_id = os.getenv("MYRA_ENTITY_MODEL_ID")
    if not intent_model_id and not entity_model_id:
        print >> sys.stderr, "environment must have MYRA_ENTITY_MODEL_ID and/or MYRA_INTENT_MODEL_ID"
        sys.exit(1)
    ic = InferenceClient(
        account_id=account_id,
        account_secret=account_secret,
        intent_model_id=intent_model_id,
        entity_model_id=entity_model_id)
    if intent_model_id:
        intent = ic.getIntent(msg)
        print "intent: %s" % (intent,)
    if entity_model_id:
        entity = ic.getEntities(msg)
        print "entity: %s" % (entity,)


if __name__ == "__main__":
    main()

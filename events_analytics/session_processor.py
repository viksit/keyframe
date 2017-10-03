import sys
import json
import logging

log = logging.getLogger(__name__)

class SessionProcessorError(Exception):
    pass

def _getd(d, k, default):
    _t = d.get(k)
    if _t is None:
        return default
    return _t

def isSearchSlot(event):
    slot_id = _getd(event, "slot_id", "")
    return (_getd(event, "slot_id", "").lower().count("search") \
       and event.get("slot_type") == "slot-type-action" \
       and event.get("action_type") == "webhook")

def isSearchSurveySlot(event):
    
    return (_getd(event, "slot_id", "").lower().count("search_survey")
            and event.get("event_type") == "response"
            and event.get("slot_type") == "slot-type-input"
            and event.get("response_type") == "fill")

def processSession(session):
    """A session is a *chronological* list of events from a single session.
    Return the processed data required for analytics.
    """
    kb_results = []
    session_summary = {}
    
    lastSearch = None
    for event in session:
        log.debug("event: %s", event)
        if event["version"] < 3:
            log.info("Session contains event at version %s. Skipping this session.", event["version"])
            return None
        if isSearchSlot(event):
            log.debug("found search slot")
            d = {"session_id": event["session_id"],
                 "ts_ms": event["ts_ms"]}
            kb_results.append(d)
            # If format is not as expected, throwing exception is what I want.
            _tmp = event["payload"]["responseElements"][0]["responseMeta"]["searchAPIResult"]
            d["query"] = _tmp["original_query"]
            d["results"] = []
            for r in _tmp.get("hits", []):
                d["results"].append({
                    "title":r.get("title"),
                    "url":r.get("url"),
                    "snippets":r.get("snippets")})
            lastSearch = d
        if isSearchSurveySlot(event):
            log.debug("found search survey slot")
            if not lastSearch:
                raise SessionProcessorError(
                    "No search before survey")
            lastSearch["survey_results"] = event["payload"]["value"]
    return kb_results

                
        
def test():
    if not len(sys.argv) > 1:
        print >> sys.stderr, "Need a session file"
    session = []
    with open(sys.argv[1]) as f:
        for l in f:
            session.append(json.loads(l.strip()))
    r = processSession(session)
    print r

if __name__ == "__main__":
    logging.basicConfig()
    log.setLevel(10)
    test()

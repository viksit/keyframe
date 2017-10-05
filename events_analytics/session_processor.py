import sys
import json
import copy
import logging

#log = logging.getLogger(__name__)
log = logging.getLogger("keyframe.session_processor")

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

def getTicket(event):
    if (_getd(event, "slot_id", "").lower().count("ticket")
        and event.get("event_type") == "response"
        and event.get("ticket_filed")):
        ticket_url = event["payload"]["responseElements"][0]["responseMeta"].get("zendeskTicketUrl")
        return {"ticket_filed":True,
                "ticket_url":ticket_url}
    return None

def processSession(session):
    """A session is a *chronological* list of events from a single session.
    Return the processed data required for analytics.
    """
    kb_info = []
    session_summary = {
        "ts":None,  # seconds from epoch as float
        "kb_info": kb_info,  # [kb_search,..]
        "num_kb_queries": 0,
        "num_kb_negative_surveys": 0,
        "topic": None,
        "ticket_filed": False,
        "ticket_url": None
    }

    session_id = None
    lastSearch = None
    for event in session:
        log.debug("event: %s", event)
        if event["version"] < 3:
            log.info("Session contains event at version %s. Skipping this session.", event["version"])
            return None

        if not session_id:
            session_id = event["session_id"]
        elif session_id != event["session_id"]:
            raise SessionProcessorError(
                "current session_id: %s, new session_id: %s",
                session_id, event["session_id"])
        if not "ts_ms" in session_summary:
            session_summary["ts"] = float(event["ts_ms"])/1000
        
        if isSearchSlot(event):
            log.debug("found search slot")
            # This is the schema for each kb_search.
            kb_search = {
                "session_id": event["session_id"],
                "ts": float(event["ts_ms"])/1000,
                "query":None,
                "results":[],
            }
            kb_info.append(kb_search)
            # If format is not as expected, throwing exception is what I want.
            _tmp = event["payload"]["responseElements"][0]["responseMeta"]["searchAPIResult"]
            kb_search["query"] = _tmp["original_query"]
            for r in _tmp.get("hits", []):
                kb_search["results"].append({
                    "title":r.get("title"),
                    "url":r.get("url"),
                    "snippets":r.get("snippets")})
            lastSearch = kb_search
        if isSearchSurveySlot(event):
            log.debug("found search survey slot")
            if not lastSearch:
                raise SessionProcessorError(
                    "No search before survey")
            survey_value = event["payload"].get("value")
            lastSearch["survey_results"] = survey_value
            if survey_value.lower() in ("no", False):
                session_summary["num_kb_negative_surveys"] += 1
        zendeskTicket = getTicket(event)
        if zendeskTicket:
            session_summary.update(zendeskTicket)
        if session_summary["kb_info"]:
            session_summary["topic"] = session_summary["kb_info"][0].get("query")
            session_summary["num_kb_queries"] = len(session_summary["kb_info"])
    return session_summary

def processSession2(session):
    session_summary = processSession(session)
    session_data = copy.deepcopy(session_summary)
    session_data.pop("kb_info")
    query_data = []
    for kb_info in session_summary.get("kb_info",[]):
        query_data.append(kb_info)
    return {
        "session_summary":session_summary,
        "session_data":session_data,
        "query_data":query_data}


def test():
    if not len(sys.argv) > 1:
        print >> sys.stderr, "Need a session file"
    session = []
    with open(sys.argv[1]) as f:
        for l in f:
            session.append(json.loads(l.strip()))
    r = processSession(session)
    print json.dumps(r)

if __name__ == "__main__":
    logging.basicConfig()
    log.setLevel(10)
    test()

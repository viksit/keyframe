import sys
import json
import copy
import logging

#log = logging.getLogger(__name__)
log = logging.getLogger("keyframe.event_analytics.session_processor")

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

def getEscalate(event):
    return (_getd(event, "slot_id", "").lower().count("escalate")
            and event.get("event_type") == "response")


def getTicket(event):
    if (_getd(event, "slot_id", "").lower().count("ticket")
        and event.get("event_type") == "response"
        and event.get("ticket_filed")):
        ticket_url = event["payload"]["responseElements"][0]["responseMeta"].get("zendeskTicketUrl")
        return {"ticket_filed":True,
                "ticket_url":ticket_url}
    return None

def createTranscriptElement(ts, msgType, origin, text=None, options=None):
        return {"ts":ts,
                "msgType":msgType,  # start | cnv (conversation)
                "origin":origin,  # user | agent
                "text":text,
                "options":options}

def processSession(session):
    """A session is a *chronological* list of events from a single session.
    Return the processed data required for analytics.
    """
    kb_info = []
    transcript = []
    session_summary = {
        "account_id": None,
        "agent_id": None,
        "session_id":None,
        "ts":None,  # seconds from epoch as float
        "kb_info": kb_info,  # [kb_search,..]
        "num_kb_queries": 0,
        "num_kb_negative_surveys": 0,
        "topic": None,
        "ticket_filed": False,
        "ticket_url": None,
        "escalate": 0,
        "location_href": None ,
        "user_id": None,
        "user_info": None,
        "num_user_responses": 0,
        "transcript": transcript
    }

    session_id = None
    account_id = None
    agent_id = None
    lastSearch = None

    for event in session:
        log.debug("event: %s", event)
        if event["version"] < 3:
            log.info("Session contains event at version %s. Skipping this session.", event["version"])
            return None

        if not session_id:
            session_id = event["session_id"]
            account_id = event["account_id"]
            agent_id = event["agent_id"]
            session_summary["session_id"] = session_id
            session_summary["account_id"] = account_id
            session_summary["agent_id"] = agent_id
            session_summary["location_href"] = event["location_href"]
            session_summary["user_id"] = event["user_id"]
            session_summary["user_info"] = event["user_info"]

        elif (session_id != event["session_id"]
              or account_id != event["account_id"]
              or agent_id != event["agent_id"]):
            raise SessionProcessorError(
                "Bad data for a single session. current session_id: %s, new session_id: %s",
                session_id, event["session_id"])

        eventTs = float(event["ts_ms"])/1000
        if not session_summary.get("ts"):
            session_summary["ts"] = eventTs

        if event.get("event_type") == "request":
            if event.get("session_status") == "start":
                transcript.append(
                    createTranscriptElement(
                        ts=eventTs,
                        msgType="start",
                        origin="user"))
            else:
                text = event.get("payload", {}).get("text")
                if text:
                    session_summary["num_user_responses"] += 1
                    transcript.append(
                        createTranscriptElement(
                            ts=event["ts_ms"],
                            msgType="cnv",
                            origin="user",
                            text=text))


        if event.get("event_type") == "response" and event.get("response_type") in ["prompt", "transfermsg", "fillmsg"]:
            reE = event.get("payload", {}).get("responseElements")
            for e in reE:
                text = e.get("text")
                tl = e.get("textList")
                if tl:
                    text = "\n".join(_e for _e in tl)
                options = e.get("optionsList")
                transcript.append(
                    createTranscriptElement(
                        ts=event["ts_ms"],
                        msgType="cnv",
                        origin="agent",
                        text=text,
                        options=options))


        if isSearchSlot(event):
            log.debug("found search slot")
            # This is the schema for each kb_search.
            kb_search = {
                "account_id": event["account_id"],
                "agent_id": event["agent_id"],
                "session_id": event["session_id"],
                "ts": float(event["ts_ms"])/1000,
                "query":None,
                "results":[],
                "survey_results":None
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
        if getEscalate(event):
            session_summary["escalate"] += 1
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

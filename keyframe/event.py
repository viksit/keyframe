from __future__ import absolute_import
import random
import time
import json

EVENT_VERSION = 4

def createEvent(**kwargs):
    _t = time.time()
    tsMs = int(round(_t*1000))
    ts = int(round(_t))
    eventType = kwargs.get("eventType")
    assert eventType, "must have eventType to create an event"
    eventId = Event.createEventId(eventType, ts)
    assert "ts" not in kwargs
    assert "eventId" not in kwargs
    kwargs["ts"] = ts
    kwargs["tsMs"] = tsMs
    kwargs["eventId"] = eventId
    return Event(**kwargs)

class Event(object):
    @classmethod
    def createEventId(cls, eventType, ts):
        return "kf_%s_%i_%i" % (
            eventType, ts, random.randint(0,1000))

    def __init__(self, **kwargs):
        self.accountId = kwargs.get("accountId")
        self.agentId = kwargs.get("agentId")
        self.version = kwargs.get("version")  # integer
        if not self.version:
            self.version = EVENT_VERSION
        self.eventType = kwargs.get("eventType")  # request, response
        self.src = kwargs.get("src")  # user, widget, agent
        self.sessionStatus = kwargs.get("sessionStatus")  # start, end
        self.eventId = kwargs.get("eventId")
        self.sessionId = kwargs.get("sessionId")
        self.userId = kwargs.get("userId")
        self.ts = kwargs.get("ts")
        self.tsMs = kwargs.get("tsMs")
        self.topicId = kwargs.get("topicId")
        self.topicType = kwargs.get("topicType")
        self.slotId = kwargs.get("slotId")
        self.slotCanonicalId = kwargs.get("slotCanonicalId")
        self.slotTags = kwargs.get("slotTags")
        self.slotType = kwargs.get("slotType")
        self.actionType = kwargs.get("actionType")
        self.responseType = kwargs.get("responseType")  # prompt, fillmsg, fillnomsg, transfermsg, 
        self.payload = kwargs.get("payload")  # must be a json-compatible data structure (i.e. string, dict)
        self.ticketFiled = kwargs.get("ticketFiled")
        self.resolutionStatus = kwargs.get("resolutionStatus")
        self.locationHref = kwargs.get("locationHref")
        self.userInfo = kwargs.get("userInfo")
        self.topicStatus = kwargs.get("topicStatus")
        self.workflowType = kwargs.get("workflowType")
        self.customProps = kwargs.get("customProps")

    def toJSON(self):
        return {
            "account_id":self.accountId,
            "agent_id":self.agentId,
            "resolution_status":self.resolutionStatus,
            "ticket_filed":self.ticketFiled,
            "version":self.version,
            "event_type":self.eventType,
            "src":self.src,
            "session_status":self.sessionStatus,
            "event_id":self.eventId,
            "session_id":self.sessionId,
            "user_id":self.userId,
            "ts":self.ts,
            "ts_ms":self.tsMs,
            "topic_id":self.topicId,
            "topic_type":self.topicType,
            "slot_id":self.slotId,
            "slot_canonical_id":self.slotCanonicalId,
            "slot_tags":self.slotTags,
            "slot_type":self.slotType,
            "action_type":self.actionType,
            "response_type":self.responseType,
            "payload":self.payload,
            "location_href":self.locationHref,
            "user_info":self.userInfo,
            "topic_status":self.topicStatus,
            "workflow_type":self.workflowType,
            "custom_props":self.customProps}

    def toJSONStr(self):
        return json.dumps(self.toJSON())

    def __repr__(self):
        return json.dumps(
            self.toJSON(), sort_keys=True, indent=2,
            separators=(',', ': '))

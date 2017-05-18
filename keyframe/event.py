import random
import time
import json

def createEvent(**kwargs):
    ts = int(round(time.time()*1000))
    eventType = kwargs.get("eventType")
    assert eventType, "must have eventType to create an event"
    eventId = Event.createEventId(eventType, ts)
    assert "ts" not in kwargs
    assert "eventId" not in kwargs
    kwargs["ts"] = ts
    kwargs["eventId"] = eventId
    return Event(**kwargs)

class Event(object):
    @classmethod
    def createEventId(cls, eventType, ts):
        return "kf_%s_%i_%i" % (
            eventType, ts, random.randint(0,1000))

    def __init__(self, **kwargs):
        self.eventType = kwargs.get("eventType")  # request, response
        self.src = kwargs.get("src")  # user, widget, agent
        self.sessionStatus = kwargs.get("sessionStatus")  # start, end
        self.eventId = kwargs.get("eventId")
        self.sessionId = kwargs.get("sessionId")
        self.userId = kwargs.get("userId")
        self.ts = kwargs.get("ts")
        self.topicId = kwargs.get("topicId")
        self.topicType = kwargs.get("topicType")
        self.slotId = kwargs.get("slotId")
        self.slotType = kwargs.get("slotType")
        self.actionType = kwargs.get("actionType")
        self.responseType = kwargs.get("responseType")  # prompt, fill
        self.payload = kwargs.get("payload")  # must be a json-compatible data structure (i.e. string, dict)

    def toJSON(self):
        return {
            "event_type":self.eventType,
            "src":self.src,
            "session_status":self.sessionStatus,
            "event_id":self.eventId,
            "session_id":self.sessionId,
            "user_id":self.userId,
            "ts":self.ts,
            "topic_id":self.topicId,
            "topic_type":self.topicType,
            "slot_id":self.slotId,
            "slot_type":self.slotType,
            "action_type":self.actionType,
            "response_type":self.responseType,
            "payload":self.payload}

    def toJSONStr(self):
        return json.dumps(self.toJSON())

    def __repr__(self):
        return json.dumps(
            self.toJSON(), sort_keys=True, indent=2,
            separators=(',', ': '))

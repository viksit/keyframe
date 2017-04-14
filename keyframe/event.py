import time
import json
import datetime
import logging

from . import messages
from . import utils

log = logging.getLogger(__name__)

def createEventId(eventType):
    return "%s_%s" % (eventType, utils.getUUID())

# def writeRequestEvent(
#         intentId, canonicalMsg, seq=0, eventWriter=None):
#     e = createRequestEvent(
#         intentId, canonicalMsg, seq)
#     if not eventWriter:
#         eventWriter = getDefaultEventWriter()
#     eventWriter.write(e)
#     return e

def createRequestEvent(
        intentId, canonicalMsg, eventResult, seq=0):
    e = RequestEvent(
        ts=utils.getTimestampMillis(),
        seq=seq,
        eventId=createEventId(Event.TYPE_REQUEST),
        intentId=intentId,
        canonicalMsg=canonicalMsg,
        eventResult=eventResult)
    return e

def createResponseEvent(
        intentId, canonicalResponse, responseClass, seq=0):
    e = ResponseEvent(
        ts=utils.getTimestampMillis(),
        seq=seq,
        eventId=createEventId(Event.TYPE_RESPONSE),
        intentId=intentId,
        canonicalResponse=canonicalResponse,
        responseClass=responseClass)
    return e



class Event(object):
    TYPE_REQUEST = "request"
    TYPE_RESPONSE = "response"
    TYPES = [TYPE_REQUEST, TYPE_RESPONSE]

    def __init__(self, **kwargs):
        #self.eventType = kwargs.get("eventType")
        self.eventSrc = kwargs.get("src")
        self.ts = kwargs.get("ts")
        self.seq = kwargs.get("seq")
        self.eventId = kwargs.get("eventId")
        self.intentId = kwargs.get("intentId")

    def toJSON(self):
        return {
            "eventSrc":self.eventSrc,
            "ts":self.ts,
            "seq":self.seq,
            "eventId":self.eventId,
            "intentId":self.intentId}

    def __repr__(self):
        return json.dumps(
            self.toJson(), sort_keys=True, indent=2,
            separators=(',', ': '))


class RequestEvent(Event):
    RESULT_NEW_INTENT = "new-intent"
    RESULT_ANSWER = "answer"
    RESULTS = [RESULT_NEW_INTENT, RESULT_ANSWER]

    def __init__(self, **kwargs):
        super(RequestEvent, self).__init__(**kwargs)
        self.eventType = Event.TYPE_REQUEST
        self.canonicalMsg = kwargs.get("canonicalMsg")
        self.eventResult = kwargs.get("eventResult")
        assert self.eventResult in self.RESULTS

    def toJSON(self):
        d = super(RequestEvent, self).toJSON()
        d2 = {
            "eventType":self.eventType,
            "canonicalMsg":self.canonicalMsg.toJSON(),
            "eventResult":self.eventResult}
        d.update(d2)
        return d
        
class ResponseEvent(Event):
    RESPONSE_CLASS_QUESTION = "question"
    RESPONSE_CLASS_INFO = "info"
    RESPONSE_CLASS_ANSWER = "answer"
    RESPONSE_CLASS_INTENT_RESPONSE = "intent_response"

    def __init__(self, **kwargs):
        super(ResponseEvent, self).__init__(**kwargs)
        self.eventType = Event.TYPE_RESPONSE
        self.canonicalResponse = kwargs.get("canonicalResponse")
        self.responseClass = kwargs.get("responseClass")

    def toJSON(self):
        d = super(ResponseEvent, self).toJSON()
        d2 = {
            "eventType":self.eventType,
            "canonicalResponse":self.canonicalResponse.toJSON(),
            "responseClass":self.responseClass}
        d.update(d2)
        return d


def getDefaultEventWriter():
    # TODO: use env vars to return the right EventWriter.
    # For now, just give back a FileEventWriter
    filename = "/mnt/tmp/ke_%s.txt" % (
        datetime.datetime.now().strftime("%Y%m%d%H%M%S"),)
    return FileEventWriter(filename)

def getDefaultEventSequencer(eventWriter=None):
    if not eventWriter:
        eventWriter = getDefaultEventWriter()
    return EventSequencer(eventWriter)

# Singleton event sequencer. The same sequencer must be used to get
# events at the same time (in milliseconds) in sequence.
_eventSequencer = None
def getEventSequencer():
    global _eventSequencer
    if _eventSequencer:
        return _eventSequencer
    _eventSequencer = getDefaultEventSequencer()
    return _eventSequencer

# Note - this is not intended to be thread-safe.
# Assumption is we're not running this in a multi-threaded environment.
class EventSequencer(object):
    """Write out an event.
    """
    def __init__(self, eventWriter=None):
        self.eventWriter = eventWriter
        if not self.eventWriter:
            self.eventWriter = getDefaultEventWriter()
        self.seq = 0

    def write(self, event):
        event.seq = self.seq
        self.seq += 1
        self.eventWriter.write(event)


class EventWriter(object):
    def write(self, event):
        raise NotImplemented()

    def close(self):
        pass

class FileEventWriter(EventWriter):
    def __init__(self, filename=None):
        self.filename = filename
        if not filename:
            filename = "/mnt/tmp/ke_%s.txt" % (
                datetime.datetime.now().strftime("%Y%m%d%H%M%S"),)
        self.fd = None

    def _open(self):
        if not self.fd or self.fd.closed:
            self.fd = open(self.filename, "w+")

    def write(self, event):
        self._open()
        jsonObject = event.toJSON()
        self.fd.write(json.dumps(jsonObject))
        self.fd.write("\n")
        self.fd.flush()

    def close(self):
        if self.fd and not self.fd.closed:
            log.debug("closing fd")
            self.fd.close()

    def __del__(self):
        self.close()



def test():
    es = EventSequencer()
    e1 = createRequestEvent(
        intentId="intent-get-refund",
        canonicalMsg=messages.CanonicalMsg(
            channel="widget",
            httpType="https",
            userId="user1",
            text="I want a refund for my last ride"),
        eventResult=RequestEvent.RESULT_NEW_INTENT)
    e2 = createResponseEvent(
        intentId="intent-get-refund",
        canonicalResponse=messages.CanonicalResponse(
            channel="widget",
            userId="user1",
            responseElements=[
                messages.ResponseElement(
                    type=messages.ResponseElement.TYPE_TEXT,
                    text=("Ok I can help you with that."
                          "Please answer the following questions."),
                    responseType=messages.ResponseElement.RESPONSE_TYPE_TRANSITIONMSG,
                    inputExpected=False)]),
        responseClass=ResponseEvent.RESPONSE_CLASS_INFO)
    e3 = createResponseEvent(
        intentId="intent-get-refund",
        canonicalResponse=messages.CanonicalResponse(
            channel="widget",
            userId="user1",
            responseElements=[
                messages.ResponseElement(
                    type=messages.ResponseElement.TYPE_OPTIONS,
                    text="How much were you charged",
                    responseType=messages.ResponseElement.RESPONSE_TYPE_SLOTFILL,
                    optionsList=["$3", "$6", "$9"],
                    displayType=messages.ResponseElement.DISPLAY_TYPE_DROPDOWN,
                    inputExpected=True)]),
        responseClass=ResponseEvent.RESPONSE_CLASS_QUESTION)
    
    es.write(e1)
    es.write(e2)
    es.write(e3)

if __name__ == "__main__":
    logging.basicConfig()
    log.setLevel(10)
    test()

                    
        
    

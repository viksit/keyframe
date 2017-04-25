import json

from . import event

EREQ = event.RequestEvent
ERES = event.ResponseEvent
EE = event.Event

class SessionAggregator(object):
    # intent state
    IS_PROC = "is_processing"
    IS_ANSWERED = "is_answered"
    IS_RESPONDED = "is_responded"

    def __init__(self):
        # metrics
        self.numIntents = 0

        # Intent was changed by the user before any resolution.
        self.changedIntents = 0

        # User abandoned the intent by being unresponsive.
        # TODO: What about if user asks for help?
        self.abandonedIntents = 0

        # Intent was provided an answer.
        self.answeredIntents = 0

        # Intent was resolved (i.e. reached the response for the intent).
        self.resolvedIntents = 0

        # We know that the user was satisfied wrt their intent.
        self.satisfiedIntents = 0

        # Total number of interactions the user did in this session.
        self.interactions = 0

        # state
        self.currentIntentState = None

        # housekeeping
        self.lastEvent = None

    def processEvent(self, e):
        """Process events in a session in chronological order.
        """
        # We should never get an event in the middle of an intent without
        # getting the start of that intent. What if we do?

        # TODO: check lastEvent < e if lastEvent otherwise exception
        if e.eventType == EE.TYPE_REQUEST:
            # TODO: may need to check eventSrc as well?
            self.interactions += 1
            if e.eventResult == EREQ.RESULT_NEW_INTENT:
                self.numIntents += 1
                if self.currentIntentState == self.IS_PROC:
                    self.changedIntents += 1
                self.currentIntentState = self.IS_PROC
            else:
                assert e.eventResult == EREQ.RESULT_ANSWER, "bad eventResult (%s)" % (e.eventResult,)

        elif e.eventType == EE.TYPE_RESPONSE:
            if e.responseClass == ERES.RESPONSE_CLASS_ANSWER:
                self.answeredIntents += 1
                self.currentIntentState = self.IS_ANSWERED
            elif e.responseClass == ERES.RESPONSE_CLASS_INTENT_RESPONSE:
                self.resolvedIntents += 1
                self.currentIntentState = self.IS_RESPONDED

    def endSession(self):
        if self.currentIntentState == self.IS_PROC:
            self.abandonedIntents += 1

    def toJSON(self):
        return {
            "numIntents":self.numIntents,
            "changedIntents":self.changedIntents,
            "abandonedIntents":self.abandonedIntents,
            "answeredIntents":self.answeredIntents,
            "resolvedIntents":self.resolvedIntents,
            "interactions":self.interactions
        }

    def __repr__(self):
        return json.dumps(self.toJSON(), indent=2, separators=(',', ': '))

def testMetrics():
    events = event.testCreateEvents()  # Need to be from the same user
    sa = SessionAggregator()
    for e in events:
        sa.processEvent(e)
    sa.endSession()
    return sa

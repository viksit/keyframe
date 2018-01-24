import event
import event_writer


def handleEvent(e, config):
    eventType = e.get("event_type")
    if e.get("event_type") == "url_click":
        handleClickEvent(e, config)
    else:
        raise Exception("Unknown event_type (%s)" % (eventType,))

def handleClickEvent(e, config):
    userId = e.get("user_id")
    assert userId, "Event must have user_id"
    accountId = e.get("account_id")
    agentId = e.get("agent_id")
    assert e.get("event_type") == "url_click"
    clickE = event.createEvent(
        accountId=accountId,
        agentId=agentId,
        userId=userId,
        eventType=e.get("event_type"), src="user",
        payload={"target_href":e.get("target_href"),
                 "target_title":e.get("target_title")})
    eventWriter = event_writer.getWriter(
        streamName=config.KINESIS_STREAM_NAME)
    eventWriter.write(clickE.toJSONStr(), userId)



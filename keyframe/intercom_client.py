# intercom client
from intercom.client import Client
import logging
log = logging.getLogger(__name__)

#APP_ID="vlvh6qvv"
#ACCESS_TOKEN="dG9rOmEyNzY2Mzk5X2NjNGRfNDY5OF9hZTMyXzgyOGE1MWFmODQ2ODoxOjA="

class IntercomClient(object):
    def __init__(self, accessToken):
        self.accessToken = accessToken

    def sendResponse(self, text, conversationId):
        log.info("IntercomClient.sendResponse(%s)", locals())
        log.info("accessToken: %s", self.accessToken)
        intercom = Client(personal_access_token=self.accessToken)
        log.info("sending response to intercom API: %s, %s", text, conversationId)
        conversation = intercom.conversations.find(id=conversationId)
        log.info("CONVERSATION: %s", conversation)
        res = intercom.conversations.reply(
            id=conversation.id,
            type=conversation.assignee.resource_type,
            admin_id=conversation.assignee.id,
            message_type='comment',
            body=text)
        return res

    def reassignConversation(self, conversationId, assigneeId, adminId):
        intercom = Client(personal_access_token=self.accessToken)
        intercom.conversations.assign(
            id=conversationId, admin_id=adminId, assignee_id=assigneeId)

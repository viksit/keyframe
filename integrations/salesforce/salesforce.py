import os, sys
import requests
import json
import tempfile
import logging
import re

from simple_salesforce import Salesforce
from simple_salesforce import SalesforceResourceNotFound

import keyframe.config
import keyframe.integrations.salesforce.salesforce as sf

log = logging.getLogger(__name__)
#log.setLevel(10)

class SalesforceClientError(Exception):
    pass


class SalesforceClient(object):
    def __init__(self, username, password, orgId, securityToken, instance):
        self.username = username
        self.password = password
        self.orgId = orgId
        self.securityToken = securityToken
        self.instance = instance
        self.sf = Salesforce(
            password=self.password,
            username=self.username,
            organizationId=self.orgId,
            security_token=self.securityToken)

    def getContact(self, email):
        """
        Returns a Contact if exists, otherwise returns None.
        """
        try:
            c = self.sf.Contact.get_by_custom_id(
                'Email', email)
            return c
        except SalesforceResourceNotFound as srne:
            return None

    def createContact(self, email, lastname, firstname):
        """
        Creates a new contact with email and name and returns the Contact.
        """
        d = self.sf.Contact.create(
            {'LastName':lastname, 'FirstName':firstname, 'Email':email})
        c = self.sf.Contact.get_by_custom_id('Email', email)
        return c

    def createTicket(self, subject, body,
                     requesterLastName,
                     requesterEmail,
                     requesterFirstName=None,
                     attachments=None):
        """
        Return id and url of the ticket.
        """
        log.debug("createTicket(%s)", locals())
        contact = self.getContact(requesterEmail)
        if not contact:
            contact = self.createContact(
                requesterEmail, requesterLastName, requesterFirstName)
        log.info("contact.get('Id'): %s", contact.get('Id'))
        ticket = self._createTicket(subject, body, contact, attachments)
        ticketUrl = "https://%s/%s" % (self.instance, ticket.get("Id"))
        return (ticket, ticketUrl)

    def _createTicket(self, subject, body, contact, attachments=None):
        log.debug("_createTicket(%s)", locals())
        caseD = {"ContactId":contact.get("Id"),
                 "Description":body,
                 "Status":"New",
                 "Subject":subject}
        log.info("caseD: %s", caseD)
        c = self.sf.Case.create(caseD)
        log.info("c: %s", c)
        case = self.sf.Case.get_by_custom_id('id', c.get("id"))
        return case
        


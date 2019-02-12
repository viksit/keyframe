import os, sys
import requests
import json
import tempfile
import logging
import re
import base64
import urllib
import os.path
import six

from simple_salesforce import Salesforce
from simple_salesforce import SalesforceResourceNotFound

import keyframe.config
import keyframe.utils

log = logging.getLogger(__name__)
#log.setLevel(10)
log.info("salesforce logging INFO")

class SalesforceError(Exception):
    pass


def createSalesforceClient(js):
    return SalesforceClient(
        username=js.get("username"), password=js.get("password"),
        orgId=js.get("org_id"), securityToken=js.get("security_token"),
        instance=js.get("instance"), domain=js.get("domain"))

class SalesforceClient(object):
    def __init__(self, username, password, orgId, securityToken, instance, domain=None):
        self.username = username
        self.password = password
        self.orgId = orgId
        self.securityToken = securityToken
        self.instance = instance
        self.domain = domain
        self.sf = Salesforce(
            password=self.password,
            username=self.username,
            organizationId=self.orgId,
            security_token=self.securityToken,
            domain=self.domain)

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
        Parameters
        attachments: list of (url, name) to be attached to the ticket.
        Return ticket struct and url of the ticket.
        """
        log.info("createTicket(%s)", locals())
        contact = self.getContact(requesterEmail)
        if not contact:
            contact = self.createContact(
                requesterEmail, requesterLastName, requesterFirstName)
        log.info("contact.get('Id'): %s", contact.get('Id'))
        ticket = self._createTicket(subject, body, contact, attachments)
        ticketUrl = "https://%s/%s" % (self.instance, ticket.get("Id"))
        if attachments:
            for (aUrl, aName) in attachments:
                log.info("creating attachment for url: %s, name: %s", aUrl, aName)
                (fd, contentType) = keyframe.utils.urlToFD(
                    url=aUrl, sizeLimitBytes=None)
                a = self._createAttachment(
                    aName, fd, ticket.get("Id"))
        return (ticket, ticketUrl)

    def _createTicket(self, subject, body, contact, attachments=None):
        log.info("_createTicket(%s)", locals())
        caseD = {"ContactId":contact.get("Id"),
                 "Description":body,
                 "Status":"New",
                 "Subject":subject,
        }
        log.info("caseD: %s", caseD)
        c = self.sf.Case.create(caseD)
        log.info("c: %s", c)
        case = self.sf.Case.get_by_custom_id('id', c.get("id"))
        return case

    def createAttachment(self, name, uri, parentId):
        fd = None
        if uri.startswith("http"):
            (fd, contentType) = keyframe.utils.urlToFD(
                url=uri, sizeLimitBytes=None)
        else:
            if os.path.exists(uri):
                fd = open(uri, "rb")
        return self._createAttachment(name, fd, parentId)

    def _createAttachment(self, name, body, parentId):
        """
        Params
        name: (str) name of the attachment (i.e. screenshot.png)
        body: the attachment itself as a filelike object that can be read as a binary blob.
        parentId: eg: the id of a ticket to which this attachment should be associated.
        """
        log.info("_createAttachment(name=%s, parentId=%s, body=...", name, parentId)
        # TODO: get this from the salesforce instance
        url = 'https://%s/services/data/v38.0/sobjects/Attachment/' % (self.instance,)
        entdoc = {
            'ParentId': parentId,
            'Name': name
        }
        entdocjson = json.dumps(entdoc)

        mimeType = keyframe.utils.getContentType(name)
        files = {
            'Body': (name, body, mimeType),
            'entity_document': (None, entdocjson, "application/json")
        }

        headers = {'Authorization': 'Bearer %s' % self.sf.session_id }
        response = requests.post(
            url = url,
            headers = headers,
            files = files
        )

        if response.status_code not in (200, 201) or not response.json().get("success"):
            log.error(response.text)
            raise Exception("Could not upload attachment")

        return response.json().get("id")

def _nameParts(name):
    # TODO: improve this.
    s = name.split()
    if len(s) > 1:
        return (s[0], s[-1])
    return (None, name)

def createTicket(jsonObject):
    """Take a jsonObject that specifies everything about the ticket
    that needs to be logged, and returns a url for the ticket.
    jsonObject: (object) dict as jsonObjectFormatExample
    Returns: {"ticket":{"url":URL}}
    """
    log.info("jsonObject: %s", jsonObject)
    j = jsonObject
    # Must have the fields to create a client. Only thing to do would be
    # to check and throw back a specific exception.
    s = createSalesforceClient(j)
    if not j.get("subject") or not j.get("body") or not j.get("requester_email"):
        raise SalesforceError("No subject or body or requester_email")
    (firstName, lastName) = _nameParts(j.get("requester_name"))
    attachments = None
    if "attachments" in j:
        attachments = _extractUrlNameFromUrls(j["attachments"])
    log.info("attachments: %s", attachments)
    (t, url) = s.createTicket(
        subject=j.get("subject"),
        body=j.get("body"),
        requesterLastName=lastName,
        requesterEmail=j.get("requester_email"),
        requesterFirstName=firstName,
        attachments=attachments)
    return {"ticket":{"url":url, "ticket":t}}


def _extractUrlNameFromUrls(urls):
    """
    Parameters
    urls: a string with comma-separated urls pointing to files.
    Returns
    [(url,name) i.e. [('http://foo.com/bar/baz.pdf', 'baz.pdf')]
    """
    # Example input:  http://foo.com/bar/0110101__baz.pdf,http://foo.com/bar/29282822__rab.pdf
    # Returns: [('http://foo.com/bar/baz.pdf','baz.pdf'), ('http://foo.com/bar/rab.pdf','rab.pdf')]
    attachments = []
    for u in urls.strip().split(','):
        u2 = urllib.parse.urlparse(u)  # http://foo.com/bar/baz.pd -> path: /bar/baz.pd 
        #ext = os.path.splitext(u2.path)[1]  # ext = .pd
        name = os.path.split(u2.path)[1]  # name = baz.pd
        # Urls from the widget upload need the '__' split.
        u3 = name.rsplit("__", 1)
        if len(u3) == 2:
            name = six.moves.urllib.parse.unquote_plus(u3[1])
        attachments.append((u, name))
    return attachments

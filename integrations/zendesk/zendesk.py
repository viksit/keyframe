import os, sys
import requests
import json
import tempfile
import logging

import zdesk

log = logging.getLogger(__name__)
#log.setLevel(10)

class ZendeskClientError(Exception):
    pass

def urlToFD2(url, sizeLimitBytes=None, chunkSize=100000):
    f = tempfile.TemporaryFile()
    r = requests.get(url, stream=True)
    if not r.status_code in (200, 201):
        raise Exception("could not get url. status_code: %s" % (r.status_code,))
    for chunk in r.iter_content(chunk_size=chunkSize):
        f.write(chunk)
        log.debug("got chunk (%s)", f.tell())
    f.seek(0)
    return (f, r.headers.get("Content-Type"))

def urlToFD(url, sizeLimitBytes=None, chunkSize=100000):
    f = tempfile.TemporaryFile()
    r = requests.get(url)
    if not r.status_code in (200, 201):
        raise Exception("could not get url. status_code: %s" % (r.status_code,))
    f.write(r.content)
    f.seek(0)
    return (f, r.headers.get("Content-Type"))

def urlToFD5(url, sizeLimitBytes=None, chunkSize=100000):
    f = open("/tmp/%s", "wb")
    r = requests.get(url)
    if not r.status_code in (200, 201):
        raise Exception("could not get url. status_code: %s" % (r.status_code,))
    f.write(r.content)
    f.close()
    return (f, r.headers.get("Content-Type"))

DEFAULT_ATTACHMENT_SIZE_LIMIT_BYTES = 1024*1024*10  # 10 MB
DEFAULT_ATTACHMENT_DOWNLOAD_CHUNK_SIZE = 1024*100  # 100 KB
defaultAttachmentsConfig = {
    "attachment_size_limit_bytes":DEFAULT_ATTACHMENT_SIZE_LIMIT_BYTES,
    "attachment_download_chunk_size":DEFAULT_ATTACHMENT_DOWNLOAD_CHUNK_SIZE,
}

class ZendeskClient(object):
    def __init__(self, apiHost, auth, attachmentsConfig=None):
        """Create a ZendeskClient
        apiHost: (string) https://lyft1450739301.zendesk.com
        auth: (string) example: admin.lyft@myralabs.com/token:xlk93jducjduejd
        """
        self.apiHost = apiHost.rstrip("/")
        self.auth = auth
        self.authTuple = None
        if self.auth:
            self.authTuple = tuple(auth.split(":"))
            assert len(self.authTuple) == 2, \
                "unexpected auth string (%s)" % (self.auth,)
            self.attachmentsConfig = attachmentsConfig
        if not self.attachmentsConfig:
            self.attachmentsConfig = defaultAttachmentsConfig
        self.zdeskApi = zdesk.Zendesk(
            apiHost, self.authTuple[0], self.authTuple[1], True)

    def uploadAttachment(self, src, filename):
        """Uploads the file pointed to by url as an attachment in Zendesk
        and returns a token.
        src: file to upload
        filename: name to give the uploaded file in zendesk
        Returns: (string) token of upload to include in zendesk ticket.
        """
        log.debug("uploadAttachment(%s)", locals())
        contentType = "application/binary"
        if not src.startswith("http"):
            # assume local file for now
            fd = open(src, "rb")
        else:
            (fd, contentType) = urlToFD(
                url=src,
                sizeLimitBytes=self.attachmentsConfig.get("attachment_size_limit_bytes"),
                chunkSize=self.attachmentsConfig.get("attachment_download_chunk_size"))
        log.debug("fd: %s, contentType: %s", fd, contentType)
        uploadResult = self.zdeskApi.upload_create(fd, filename=filename, mime_type=contentType, complete_response=True)
        return json.loads(uploadResult["content"])["upload"]["token"]

    def createTicket(self, subject, body, requesterName, requesterEmail,
                     attachments=None):
        """Create a zendesk ticket and return a url for the ticket.
        subject: (string)
        body: (string)
        requesterName: (string)
        requesterEmail: (string)
        attachments: (list of string) ["http://foo/bar.jpg",..]
                     currently only attachments available over http are supported.
        Returns:
          (string) eg: https://lyft1450739301.zendesk.com/api/v2/tickets/442.json
        """
        log.debug("createTicket(%s)", locals())
        # First upload attachments to zendesk and get tokens
        uploadTokens = []
        if attachments:
            for a in attachments:
                t = self.uploadAttachment(src=a, filename=os.path.basename(a))
                uploadTokens.append(t)

        return self._createTicket(subject, body, requesterName, requesterEmail,
                             uploadTokens)

    def _createTicket(self, subject, body, requesterName, requesterEmail,
                      uploadTokens):
        ticketJson = {
            "ticket":{
                "requester":{
                    "name":requesterName,
                    "email":requesterEmail
                },
                "subject":subject,
                "comment":{
                    "body":body,
                    # "uploads":uploadTokens  # uploads don't work with zdesk on ticket creation
                }
            }
        }
        log.debug("ticketJson: %s", ticketJson)
        r = self.zdeskApi.ticket_create(ticketJson, complete_response=True)
        log.debug("zdeskApi.ticket_create returned: %s", r)
        if uploadTokens:
            # update the ticket. this seems to work.
            ticketId = r["content"]["ticket"]["id"]
            updateJson = {"ticket":{
                "comment":{"body":"attachment",
                           "uploads":uploadTokens},
                "id":ticketId}}
            updateResult = self.zdeskApi.ticket_update(
                ticketId, updateJson)
            log.debug("updateResult: %s", updateResult)

        return r["content"]

jsonObjectFormatExample = {
    "api_host": "https://lyft1450739301.zendesk.com",
    "auth": "admin.lyft@myralabs.com/token:xld8shasfks8uebndsk",
    "subject":"Request for refund",
    "body": "I was charged incorrectly for this service.",
    "requester_name": "MyraLabs Test",
    "requester_email": "nishant@myralabs.com",
    "attachments":["http://one", "http://two"]
}

def createTicket(jsonObject):
    """Take a jsonObject that specifies everything about the ticket
    that needs to be logged, and returns a url for the ticket.
    jsonObject: (object) dict as jsonObjectFormatExample
    Returns: (string)
    """
    j = jsonObject
    z = ZendeskClient(j.get("api_host"), j.get("auth"))
    ticketResponse = z.createTicket(
        subject=j.get("subject"),
        body=j.get("body"),
        requesterEmail=j.get("requester_email"),
        requesterName=j.get("requester_name")
        #attachments=j.get("attachments")
    )
    return ticketResponse

def test():
    if len(sys.argv) < 2:
        print >> sys.stderr, "usage: zendesk.py /path/to/ticket.json"
        sys.exit(1)
    zendeskJsonFile = sys.argv[1]
    ticketJsonObject = json.loads(open(zendeskJsonFile).read())
    ticketResponse = createTicket(ticketJsonObject)
    #print "ticketResponse: %s" % (ticketResponse,)
    print "ticket.url: %s" % (ticketResponse.get("ticket", {}).get("url"),)

if __name__ == "__main__":
    logging.basicConfig()
    log = logging.getLogger()
    log.setLevel(10)
    test()

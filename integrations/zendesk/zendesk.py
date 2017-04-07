import os, sys
import requests
import json
import tempfile
import logging

log = logging.getLogger(__name__)

class ZendeskClientError(Exception):
    pass

def urlToFD(url, sizeLimitBytes=None, chunkSize=100000):
    f = tempfile.TemporaryFile()
    r = requests.get(url, stream=True)
    if not r.status_code in (200, 201):
        raise Exception("could not get url. status_code: %s" % (r.status_code,))
    for chunk in r.iter_content(chunk_size=chunkSize):
        f.write(chunk)
        log.debug("got chunk (%s)", f.tell())
    f.seek(0)
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

    def uploadAttachment(self, url, filename):
        """Uploads the file pointed to by url as an attachment in Zendesk
        and returns a token.
        url: file to upload
        filename: name to give the uploaded file in zendesk
        Returns: (string) token of upload to include in zendesk ticket.
        """
        if not url.startswith("http"):
            raise ZendeskClientError("unsupported attachment format")
        (fd, contentType) = urlToFD(
            url=url,
            sizeLimitBytes=self.attachmentsConfig.get("attachment_size_limit_bytes"),
            chunkSize=self.attachmentsConfig.get("attachment_download_chunk_size"))
        uploadUrl = "%s/api/v2/uploads.json?filename=%s" % (
            self.apiHost, filename)
        log.info("uploadUrl: %s, auth: %s", uploadUrl, self.authTuple)
        r = requests.post(uploadUrl, auth=self.authTuple, files={"f1":fd})
        if r.status_code not in (200, 201):
            log.exception(r.text)
            raise Exception("could not upload file using %s" % (uploadUrl,))
        token = r.json().get("upload",{}).get("token")
        if not token:
            raise Exception("could not get token for uploaded file", data=r.json())
        return token

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
        # First upload attachments to zendesk and get tokens
        uploadTokens = []
        if attachments:
            for a in attachments:
                t = self.uploadAttachment(url=a, filename=os.path.basename(a))
                uploadTokens.append(t)

        ticketJson = {
            "ticket":{
                "requester":{
                    "name":requesterName,
                    "email":requesterEmail
                },
                "subject":subject,
                "comment":{
                    "body":body,
                    "uploads":uploadTokens
                }
            }
        }
        ticketUrl = "%s/api/v2/tickets.json" % (self.apiHost,)
        log.info("calling zendesk: ticketUrl: %s, auth: %s",
                 ticketUrl, self.authTuple)
        log.debug("calling zendesk: json: %s", ticketJson)
        response = requests.post(ticketUrl, json=ticketJson, auth=self.authTuple)
        if response.status_code not in (200, 201, 202):
            log.exception(response.text)
            raise Exception("zendesk ticket api call failed. status_code: %s" % (response.status_code,))
        log.info("response (%s): %s" % (type(response), response))
        responseJsonObj = {}
        try:
            responseJsonObj = response.json()
        except ValueError as ve:
            log.warn("could not get json from response to webhook")
        return responseJsonObj

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
        requesterName=j.get("requester_name"),
        attachments=j.get("attachments"))
    return ticketResponse

def test():
    if len(sys.argv) < 2:
        print >> sys.stderr, "usage: zendesk.py /path/to/ticket.json"
        sys.exit(1)
    zendeskJsonFile = sys.argv[1]
    ticketJsonObject = json.loads(open(zendeskJsonFile).read())
    ticketUrl = createTicket(ticketJsonObject)
    print "ticketUrl: %s" % (ticketUrl,)

if __name__ == "__main__":
    logging.basicConfig()
    log = logging.getLogger(__name__)
    log.setLevel(10)
    test()

import base64
import json
import sys, os
import logging

from flask import Flask, Response  # , request, session, render_template, jsonify, redirect, url_for, send_from_directory, jsonify, make_response, send_file

import s3_writer
import config

logging.basicConfig()
log = logging.getLogger("lambda_event_handler")
log.setLevel(20)

app = Flask(__name__)
cfg = config.getConfig()

@app.route("/ping", methods=["GET", "POST"])
def ping():
    log.info("received ping")
    resp = json.dumps({
        "status": "OK",
        "REALM":os.getenv("REALM"),
        "STAGE":os.getenv("STAGE")
    })
    return Response(resp), 200


def lambda_handler(kevent, context):
    log.info("kevent: %s", kevent)
    log.info("context: %s", context)
    s3Writer = s3_writer.S3Writer(
        s3Bucket = os.getenv("S3_BUCKET", "ml-logs-dev")
    )

    decoded_record_data = [base64.b64decode(record['kinesis']['data']) for record in kevent['Records']]
    log.info("decoded_record_data: %s", decoded_record_data)
    handle_records(decoded_record_data)

def eventfile_handler(eventsFile):
    log.info("eventsFile: %s", eventsFile)
    events = []
    with open(eventsFile) as f:
        for l in f:
            e = l.strip()
            events.append(e)
    handle_records(events)

def handle_records(records):
    log.info("handle_records VERSION 1")
    accountEvents = {}
    for e in records:
        s3Prefix = "unknown"
        try:
            j = json.loads(e)
            if "account_id" in j:
                s3Prefix = j.get("account_id")
        except Exception as e:
            log.error("could not decode event as json: %s", e)
            s3Prefix = "error"
        events = accountEvents.setdefault(s3Prefix, [])
        events.append(e)

    # Now write all events to s3
    #cfg = config.getConfig()
    s3Writer = s3_writer.S3Writer(cfg.KF_EVENTS_S3_BUCKET)
    log.info("created s3Writer for bucket: %s", cfg.KF_EVENTS_S3_BUCKET)
    for (k,v) in accountEvents.iteritems():
        s3Prefix = "accounts/%s" % (k,)
        log.info("writing data at s3Prefix: %s", s3Prefix)
        log.debug("data: %s", v)
        s3Writer.writeData(s3Prefix=s3Prefix, data=v)
    log.info("all data written")


def _process_file():
    assert len(sys.argv) == 2, "need file to process"
    eventfile_handler(sys.argv[1])

if __name__ == "__main__":
    _process_file()

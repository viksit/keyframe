import sys
import json
import plac
import logging
import dateutil
import dateutil.parser
import datetime

import boto
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from boto.s3.bucketlistresultset import BucketListResultSet

#from pyspark import SparkContext
from pyspark.sql import SparkSession

import session_processor
import db_api
import config

log = logging.getLogger(__name__)
log = logging.getLogger("keyframe.event_analytics.spark_event_processor")

def _get_sessions(cfg, eventsPathList):
    log.info("_get_sessions(%s)", locals())
    if not eventsPathList:
        return []
    spark = SparkSession \
            .builder \
            .appName("Python Spark SQL basic example") \
            .config("spark.some.config.option", "some-value") \
            .getOrCreate()
    sc = spark.sparkContext
    sc._jsc.hadoopConfiguration().set(
        "fs.s3n.awsAccessKeyId", cfg.AWS_ACCESS_KEY_ID)
    sc._jsc.hadoopConfiguration().set(
        "fs.s3n.awsSecretAccessKey", cfg.AWS_SECRET_ACCESS_KEY)
    log.info("reading events from eventsPath")
    df = spark.read.json(eventsPathList)
    log.info("total events: %s", df.count())
    rdd1 = df.rdd
    sessions = rdd1.map(lambda x: (x['session_id'], x)).groupByKey().collect()
    return sessions


def process_sessions(cfg, eventsPathList, dates=None):
    """Create sessions for the events in eventsPathList that *start* on
    the dates listed. Drop any sessions that did not start on dates.
    Input
      eventsPathList: list of paths (s3 or local)
      dates: list of datetime.date
    Returns: session_summaries (json-compatible)
    """
    log.info("process_sessions(%s)", locals())
    sessions = _get_sessions(cfg, eventsPathList)
    log.info("got sessions: %s", sessions)
    sessions_summaries = {}
    for (session_id, session_rows) in sessions:
        # Sessions should not be very big so this should be ok.
        rows = [r.asDict(recursive=True) for r in session_rows]
        rows.sort(cmp=lambda a, b: cmp(a.get("ts_ms",0) , b.get("ts_ms",0)))
        log.info("for session_id %s, got rows %s", session_id, len(rows))
        if dates:
            session_start_date = datetime.datetime.utcfromtimestamp(
                        float(rows[0]["ts_ms"])/1000).date()
            if session_start_date not in dates:
                log.info("session_id %s start is %s which is not in the specified dates - dropping it.", session_id, session_start_date)
                continue
        session_summary = session_processor.processSession(rows)
        sessions_summaries[session_id] = session_summary
    return sessions_summaries

def _s3PathExists(s3Bucket, s3Prefix):
    l = s3Bucket.list(s3Prefix)
    for e in l:
        return True
    return False

def _createDates(dates):
    eventDates = []
    if not dates:
        eventDates = [datetime.datetime.utcnow().date()]
    else:
        for d in dates.strip().split(","):
            eventDates.append(dateutil.parser.parse(d).date())
    return eventDates

def generateS3Paths(cfg, accountId, eventDates):
    """Generate s3n paths to process given accountId and dates.
    cfg: Config class.
    accountId: accountId
    eventDates: [datetime.date]
    """
    conn = boto.connect_s3(cfg.AWS_ACCESS_KEY_ID, cfg.AWS_SECRET_ACCESS_KEY)
    s3b = conn.get_bucket('ml-logs-%s' % (cfg.REALM,))

    log.debug("eventDates: %s", eventDates)
    eventsPathList = []
    for d in eventDates:
        previousDay = d - datetime.timedelta(days=1)
        p = "accounts/%(accountId)s/%(dYear)s/%(dMonth)s/%(dDay)s/23" % {
            "accountId":accountId,
            "dYear":previousDay.year,
            "dMonth":"%02d"%(previousDay.month,),
            "dDay":"%02d"%(previousDay.day,)}
        log.debug("candidate path: %s", p)
        if _s3PathExists(s3b, p):
            s3np = "s3n://ml-logs-%s/%s/*" % (cfg.REALM, p)
            log.debug("adding path: %s", s3np)
            eventsPathList.append(s3np)
        p = "accounts/%(accountId)s/%(dYear)s/%(dMonth)s/%(dDay)s" % {
            "accountId":accountId,
            "dYear":d.year,
            "dMonth":"%02d"%(d.month,),
            "dDay":"%02d"%(d.day,)}
        log.debug("candidate path: %s", p)
        if _s3PathExists(s3b, p):
            s3np = "s3n://ml-logs-%s/%s/*" % (cfg.REALM, p)
            log.debug("adding path: %s", s3np)
            eventsPathList.append(s3np)
        nextDay = d + datetime.timedelta(days=1)
        p = "accounts/%(accountId)s/%(dYear)s/%(dMonth)s/%(dDay)s/00" % {
            "accountId":accountId,
            "dYear":nextDay.year,
            "dMonth":"%02d"%(nextDay.month,),
            "dDay":"%02d"%(nextDay.day,)}
        log.debug("candidate path: %s", p)
        if _s3PathExists(s3b, p):
            s3np = "s3n://ml-logs-%s/%s/*" % (cfg.REALM, p)
            log.debug("adding path: %s", s3np)
            eventsPathList.append(s3np)
    return eventsPathList


@plac.annotations(
    action=plac.Annotation(
        "Action (Required)", "positional", None, str,
        ["write-to-stdout", "write-to-db"]),
    eventsPath=plac.Annotation("Events path", "option", None, str),
    accountId=plac.Annotation("Account id", "option", None, str),
    dates=plac.Annotation("dates", "option", None, str)
)
def main(action, eventsPath=None, accountId=None, dates=None):
    assert not (eventsPath and (accountId or dates)), "Give either eventsPath or accountId and dates"
    cfg = config.getConfig()
    eventsPathList = []
    eventDates = []
    if eventsPath:
        eventsPathList = [e.strip() for e in eventsPath.strip().split(",") if e.strip()]
    if not eventsPath:
        assert accountId, "must give accountId if no eventsPath"
        eventDates = _createDates(dates)
        eventsPathList = generateS3Paths(cfg, accountId, eventDates)

    session_summaries = process_sessions(
        cfg=cfg, eventsPathList=eventsPathList, dates=eventDates)
    if action == "write-to-stdout":
        print json.dumps(session_summaries, indent=True, separators=(',', ': '))
    elif action == "write-to-db":
        dbApi = db_api.DBApi()
        dbApi.writeAll(session_summaries)
    log.info("spark_event_processor DONE")

if __name__ == "__main__":
    logging.basicConfig()
    keyframe_l = logging.getLogger("keyframe")
    keyframe_l.setLevel(10)
    log.setLevel(10)
    plac.call(main)

import sys
import json
import logging

#from pyspark import SparkContext
from pyspark.sql import SparkSession

import session_processor

log = logging.getLogger(__name__)

EVENTS_PATH = '/mnt/s3/ml-logs-prod/accounts/7BbmKJgxsMKRuAcBjNA1Zo/2017/09/*/*'

def _get_sessions(eventsPath=EVENTS_PATH):
    spark = SparkSession \
            .builder \
            .appName("Python Spark SQL basic example") \
            .config("spark.some.config.option", "some-value") \
            .getOrCreate()

    df = spark.read.json(eventsPath)
    log.info("total events: %s", df.count())
    rdd1 = df.rdd
    sessions = rdd1.map(lambda x: (x['session_id'], x)).groupByKey().collect()
    return sessions


def _convert_row(r):
    """Spark creates its own data structures from the json input.
    We want to convert it back to json-compatible structures so the rest
    of the system can work from those and not depend on spark data structures.
    (like pyspark.sql.types.Row).
    """
    x = r.asDict(recursive=True)
    if "payload" in x:
        x["payload"] = x["payload"].asDict()
    return x

def process_sessions(eventsPath=EVENTS_PATH):
    sessions = _get_sessions(eventsPath)
    sessions_summaries = {}
    sessions_data = []
    querys_data = []
    for (session_id, session_rows) in sessions:
        # Sessions should not be very big so this should be ok.
        rows = [r.asDict(recursive=True) for r in session_rows]
        rows.sort(cmp=lambda a, b: cmp(a.get("ts_ms",0) , b.get("ts_ms",0)))
        log.info("for session_id %s, got rows %s", session_id, len(rows))
        _d = session_processor.processSession2(rows)
        sessions_summaries[session_id] = _d.get("session_summary")
        sessions_data.append(_d.get("session_data"))
        querys_data.extend(_d.get("query_data"))
    return {"sessions_summaries":sessions_summaries,
            "sessions_data":sessions_data,
            "querys_data":querys_data}

if __name__ == "__main__":
    logging.basicConfig()
    keyframe_l = logging.getLogger("keyframe")
    keyframe_l.setLevel(10)
    log.setLevel(10)
    if len(sys.argv) < 2:
        print >> sys.stderr, "provide events files path"
    ss = process_sessions(eventsPath=sys.argv[1])
    print json.dumps(ss.get("querys_data"), indent=True, separators=(',', ': '))

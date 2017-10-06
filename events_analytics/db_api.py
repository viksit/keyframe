import sys, os
import psycopg2
import json

import logging

log = logging.getLogger("keyframe.db_api")

def connectToDatabase():
    realm = os.getenv("REALM", "dev")
    dbstring = None
    if realm == "dev":
        dbstring = "dbname='myra_db_dev' user='myraadmin' host='myra-db-dev.cihwyaszqq2o.us-west-2.rds.amazonaws.com' password='RZ4KvefI3f9e'"
    elif realm == "prod":
        dbstring = "dbname='myra_db_prod' user='myraadmin' host='myra-db-main.cihwyaszqq2o.us-west-2.rds.amazonaws.com' password='RZ4KvefI3f9e'"
    else:
        raise Exception("unknown REALM (%s)", realm)
    #log.info('dbstring: %s' % dbstring)
    conn = psycopg2.connect(dbstring)
    # Setting autocommit is important because we don't use conn.commit everywhere.
    conn.autocommit = True
    return conn

class DBApi(object):
    def __init__(self, dbConnection=None):
        self.dbc = dbConnection
        if not self.dbc:
            self.dbc = connectToDatabase()

    def writeSessionQueries(self, session_queries):
        """No PK for a single query. All session queries for session_id
        are first deleted and then written.
        """
        # Don't worry about transactions at least for now.
        log.debug("DBApi.writeQueries(%s)", session_queries)
        if not session_queries:
            log.info("No session queries found - returning")
            return
        with self.dbc.cursor() as cur:
            deleted = False
            for q in session_queries:
                log.debug("q: %s", q)
                if not deleted:
                    cur.execute(
                        "delete from myra2.kb_queries where session_id = %s",
                        (q["session_id"],))
                    deleted = True
                
                sql = (
                    "insert into myra2.kb_queries "
                    "(session_id, ts, query, results, num_results, survey_results) "
                    "values (%s, to_timestamp(%s), %s, %s, %s, %s)")
                results = q.get("results", [])
                num_results = len(results)
                log.info("SQL: %s", cur.mogrify(
                    sql, (q["session_id"], q["ts"], q.get("query"),
                          json.dumps(results),
                          num_results, None)))
                cur.execute(
                    sql, (q["session_id"], q["ts"], q.get("query"),
                          json.dumps(results),
                          num_results, q.get("survey_results")))
        
    def writeSession(self, session):
        log.debug("DBApi.writeSession(%s)", session)
        s = session
        with self.dbc.cursor() as cur:
            # Don't worry about transactions for now.
            cur.execute("delete from myra2.kb_sessions where session_id = %s",
                        (s["session_id"],))
            sql = (
                "insert into myra2.kb_sessions "
                "(session_id, ts, topic, num_kb_queries, num_kb_negative_surveys, ticket_url) "
                "values (%s, to_timestamp(%s), %s, %s, %s, %s)")
            log.info("SQL: %s", cur.mogrify(
                sql, (s["session_id"], s["ts"], s.get("topic"), s.get("num_kb_queries"), s.get("num_kb_negative_surveys"), s.get("ticket_url"))))
            cur.execute(
                sql, (s["session_id"], s["ts"], s.get("topic"), s.get("num_kb_queries"), s.get("num_kb_negative_surveys"), s.get("ticket_url")))


def test_sessions(f):
    sessions = json.loads(open(f).read())
    dbApi = DBApi()
    for s in sessions:
        dbApi.writeSession(s)

def test_sessions_queries(f):
    session_summaries = json.loads(open(f).read())
    dbApi = DBApi()
    for (session_id, session_summary) in session_summaries.iteritems():
        dbApi.writeSessionQueries(session_summary.get("kb_info",[]))


if __name__ == "__main__":
    logging.basicConfig()
    kf_log = logging.getLogger("keyframe")
    kf_log.setLevel(10)
    #test_sessions(sys.argv[1])
    test_sessions_queries(sys.argv[1])

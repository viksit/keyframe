from __future__ import absolute_import
import sys, os
import psycopg2
import json
import config
import logging
import six

log = logging.getLogger("keyframe.db_api")

def connectToDatabase(cfg=None):
    if not cfg:
        cfg = config.getConfig()
    dbstring = cfg.DB_CONN_STRING
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
                    "(account_id, agent_id, session_id, ts, query, results, num_results, survey_results) "
                    "values (%s, %s, %s, to_timestamp(%s), %s, %s, %s, %s)")
                results = q.get("results", [])
                num_results = len(results)
                log.info("SQL: %s", cur.mogrify(
                    sql, (q["account_id"], q["agent_id"],
                          q["session_id"], q["ts"], q.get("query"),
                          json.dumps(results),
                          num_results, None)))
                cur.execute(
                    sql, (q["account_id"], q["agent_id"],
                          q["session_id"], q["ts"], q.get("query"),
                          json.dumps(results),
                          num_results, q.get("survey_results")))
        
    def writeSession(self, session):
        log.debug("DBApi.writeSession(%s)", session)
        if not session:
            log.warn("DBApi.writeSession called with: %s", session)
            return
        s = session
        with self.dbc.cursor() as cur:
            # Don't worry about transactions for now.
            cur.execute("delete from myra2.kb_sessions where session_id = %s",
                        (s["session_id"],))
            sql = (
                "insert into myra2.kb_sessions "
                "(account_id, agent_id, session_id, ts, topic, num_kb_queries, num_kb_negative_surveys, ticket_filed, ticket_url, escalate, location_href, user_id, user_info, num_user_responses) "
                "values (%s, %s, %s, to_timestamp(%s), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
            log.info("SQL: %s", cur.mogrify(
                sql, (s["account_id"], s["agent_id"],
                      s["session_id"], s["ts"], s.get("topic"),
                      s.get("num_kb_queries"), s.get("num_kb_negative_surveys"),
                      s.get("ticket_filed"), s.get("ticket_url"),
                      s.get("escalate"), s.get("location_href"),
                      s.get("user_id"), s.get("user_info"),
                      s.get("num_user_responses"))))
            cur.execute(
                sql, (s["account_id"], s["agent_id"],
                      s["session_id"], s["ts"], s.get("topic"),
                      s.get("num_kb_queries"), s.get("num_kb_negative_surveys"),
                      s.get("ticket_filed"), s.get("ticket_url"),
                      s.get("escalate"), s.get("location_href"),
                      s.get("user_id"), s.get("user_info"),
                      s.get("num_user_responses")))

    def writeAll(self, sessions_summaries):
        for (session_id, session_summary) in six.iteritems(sessions_summaries):
            log.info("writing session_id: %s", session_id)
            if not session_summary:
                log.warn("DBApi.writeAll session_summary: %s", session_summary)
                continue
            self.writeSession(session_summary)
            self.writeSessionQueries(session_summary.get("kb_info",[]))

def test_sessions(f):
    sessions = json.loads(open(f).read())
    dbApi = DBApi()
    for (session_id, session_summary) in six.iteritems(sessions):
        dbApi.writeSession(session_summary)

def test_sessions_queries(f):
    session_summaries = json.loads(open(f).read())
    dbApi = DBApi()
    for (session_id, session_summary) in six.iteritems(session_summaries):
        dbApi.writeSessionQueries(session_summary.get("kb_info",[]))


if __name__ == "__main__":
    logging.basicConfig()
    kf_log = logging.getLogger("keyframe")
    kf_log.setLevel(10)
    test_sessions(sys.argv[1])
    test_sessions_queries(sys.argv[1])

-- sessions with number of user interactions and zendesk ticket yes/no.
-- events_prod_demo is for the demo@myralabs.com user. this makes the s3 scan
-- limited to this user vs across all users.
-- create additional tables for other users as required. the sql will be the same.
-- [Q1]
select session_id, agent_id, min(ts) session_start_time, max(ts) session_end_time,
       count(*) total_msgs,
       sum(if (event_type = 'request', 1, 0)) user_interactions,
       max(if (action_type = 'zendesk', 1, 0)) zendesk_action
from events_prod_demo  -- create tables for other users as required.
where ts_ms > to_unixtime(timestamp '2017-09-01 00:00 UTC')*1000
and agent_id = '<agent-id>'
group by session_id, agent_id
order by min(ts) desc;

-- all events for a session
-- [Q2]
SELECT *
from events_prod_demo
where session_id = '<session-id>'
order by ts_ms asc;


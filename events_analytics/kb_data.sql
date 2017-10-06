create table myra2.kb_sessions (
  account_id varchar(100) not null,
  agent_id varchar(100) not null,
  session_id varchar(100) not null primary key,
  ts timestamp with time zone not null,
  topic varchar(1000),
  num_kb_queries int,
  num_kb_negative_surveys int,
  ticket_filed boolean,
  ticket_url varchar(1000)
);

create table myra2.kb_queries (
  account_id varchar(100) not null,
  agent_id varchar(100) not null,
  session_id varchar(100) not null,
  ts timestamp with time zone not null,
  query varchar(1000),
  results json,
  num_results int,
  survey_results varchar(10)
);

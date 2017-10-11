#!/bin/bash

# This is to run even processing on a machine with a virtualenv 'analytics'.
source /home/ubuntu/events_analytics/analytics/bin/activate
source /mnt/production/myra_env_set.sh

# accountId = 7BbmKJgxsMKRuAcBjNA1Zo = demo@myralabs.com
python /home/ubuntu/events_analytics/spark_event_processor.py write-to-db -accountId 7BbmKJgxsMKRuAcBjNA1Zo


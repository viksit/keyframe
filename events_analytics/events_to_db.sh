#!/bin/bash

# This is to run even processing on a machine with a virtualenv 'analytics'.
source /home/ubuntu/events_analytics/analytics/bin/activate
source /mnt/production/myra_env_set.sh

REALM=${REALM:-"dev"}
if [[ "${REALM}" == "prod" ]]; then
    # accountId = 7BbmKJgxsMKRuAcBjNA1Zo = demo@myralabs.com
    python /home/ubuntu/events_analytics/spark_event_processor.py write-to-db -accountId 7BbmKJgxsMKRuAcBjNA1Zo
else
    python /home/ubuntu/events_analytics/spark_event_processor.py write-to-db -accountId 3rxCO9rydbBIf3DOMb9lFh  # nishant+dev
    python /home/ubuntu/events_analytics/spark_event_processor.py write-to-db -accountId 3oPxV9oFXxzHYxuvpy56a9  # viksit+dev
fi




- Configuration

Pip install pyspark==2.2.0 by itself does not allow reading files from s3. The following jars were added in addition to the requirements.txt to make things work.

s3://ml-users/nishant/pyspark/additional_jars/aws-java-sdk-s3-1.11.210.jar
s3://ml-users/nishant/pyspark/additional_jars/aws-java-sdk-core-1.11.210.jar
s3://ml-users/nishant/pyspark/additional_jars/aws-java-sdk-1.11.210.ja
s3://ml-users/nishant/pyspark/additional_jars/hadoop-aws-2.7.3.jar

- Running spark_event_processor

Data can be local or on s3. Note use s3n as prefix for s3 locations.

```
(analytics) ~/work/keyframe/events_analytics $ python ./spark_event_processor.py write-to-stdout "/mnt/s3/ml-logs-dev/accounts/3rxCO9rydbBIf3DOMb9lFh/2017/10/09/*/*"

(analytics) ~/work/keyframe/events_analytics $ python ./spark_event_processor.py write-to-stdout "s3n:///ml-logs-dev/accounts/3rxCO9rydbBIf3DOMb9lFh/2017/10/09/*/*"
```

- Deploying

```
tar -L -czf /tmp/events_analytics.tar.gz config.py db_api.py session_processor.py spark_event_processor.py events_to_db.sh

scp /tmp/events_analytics.tar.gz ubuntu@0.api.prod.myralabs.com:~/events_analytics/
```

Untar.
Check the cron works.




# THIS CODE HAS BEEN MOVED TO MYRA REPO. DO NOT ADD/CHANGE THIS CODE.

---------------------------------

## Overview

* Knowledge base analytics
  * myra2.kb_sessions: one row per session as defined by the keyframe agent.
  * myra2.kb_queries: one row per query with session_id

Create cookie ```__myra_user_info```. Its value will be added to the user_info column in the db.

## Configuration

Pip install pyspark==2.2.0 by itself does not allow reading files from s3. The following jars were added in addition to the requirements.txt to make things work.

s3://ml-users/nishant/pyspark/additional_jars/aws-java-sdk-s3-1.11.210.jar
s3://ml-users/nishant/pyspark/additional_jars/aws-java-sdk-core-1.11.210.jar
s3://ml-users/nishant/pyspark/additional_jars/aws-java-sdk-1.11.210.ja
s3://ml-users/nishant/pyspark/additional_jars/hadoop-aws-2.7.3.jar

- Running spark_event_processor

Data can be local or on s3. Note use s3n as prefix for s3 locations.

```
(myra-environment)~/work/myra $ python -m myra.v2.event_processing.keyframe.spark_event_processor write-to-db -accountId 3rxCO9rydbBIf3DOMb9lFh -dates 20171009

(myra-environment)~/work/myra $ python -m myra.v2.event_processing.keyframe.spark_event_processor write-to-stdout -eventsPath "/mnt/s3/ml-logs-dev/accounts/3rxCO9rydbBIf3DOMb9lFh/2017/10/09/*/*"

(myra-environment)~/work/myra $ python -m myra.v2.event_processing.keyframe.spark_event_processor write-to-stdout -eventsPath "s3n://ml-logs-dev/accounts/3rxCO9rydbBIf3DOMb9lFh/2017/10/09/*/*"
```

- Deploying

The code is deployed along with a deploy of the myra api.


- Possible errors:
```
17/10/11 23:41:15 ERROR SparkContext: Error initializing SparkContext. 
java.net.BindException: Cannot assign requested address: Service 'sparkDriver' failed after 16 retries (on a random free port)! Consider explicitly setting the appropri
ate binding address for the service 'sparkDriver' (for example spark.driver.bindAddress for SparkDriver) to the correct binding address.
```

Get the hostname of the machine (```hostname```) and add it to /etc/hosts:
```
127.0.0.1 <hostname>
```




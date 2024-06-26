from __future__ import absolute_import
import os
import logging
import distutils
import distutils.util

log = logging.getLogger(__name__)

# Zappa creates 'STAGE' env var based on the deploy.
# 'zappa deploy dev' => STAGE=dev
# But we do not want to use STAGE. We will use REALM which we set explicitly in the zappa_settings.py.

#TMP_REALM = os.getenv("REALM", "dev")
#REALM = os.getenv("STAGE", TMP_REALM)

REALM = os.getenv("REALM", "dev")
log.info("REALM: %s", REALM)

def getConfig(realm=None):
    log.info("getConfig(%s) called", realm)
    if not realm:
        realm = REALM
    log.info("getConfig realm: %s", realm)
    if realm == "prod":
        return ProdConfig()
    elif realm == "dev":
        return DevConfig()
    elif realm == "test":
        return TestConfig()
    else:
        raise Exception("Unknown REALM: %s" % (realm,))

class Config(object):
    REALM = REALM
    HTTP_SCHEME = os.getenv("HTTP_SCHEME", "http")
    BOTSTATE_TTL_SECONDS = int(os.getenv("BOTSTATE_TTL_SECONDS", 60*60*6))  # 6 hours
    BOTSTATE_HISTORY_TTL_SECONDS = BOTSTATE_TTL_SECONDS
    INTENT_SCORE_THRESHOLD = 0.7

    KINESIS_USER_ACCESS_KEY_ID = "AKIAII26HBVXJUNGKT5A"
    KINESIS_USER_SECRET_ACCESS_KEY = "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"
    KINESIS_AWS_REGION = "us-west-2"

    KINESIS_STREAM_PREFIX = os.getenv("KINESIS_STREAM_PREFIX","kf-events-dev")
    KINESIS_STREAM_NAME = os.getenv("KINESIS_STREAM_NAME", "kf-events-dev")

    AWS_S3_REGION = "us-west-2"
    DYNAMODB_AWS_REGION = "us-west-2"
    KV_STORE_S3_BUCKET = "ml-dev"

    KF_EVENTS_S3_BUCKET = os.getenv("KF_EVENTS_S3_BUCKET", "ml-logs-dev")

    AWS_S3_PUBLIC_UPLOAD_ACCESS_KEY_ID = "AKIAI7EIN2LNVZSF6CKA"
    AWS_S3_PUBLIC_UPLOAD_SECRET_ACCESS_KEY = "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"
    AWS_S3_PUBLIC_UPLOAD_BUCKET = "ml-public-upload-dev"

    # This is IAM user dyndb-dev
    AWS_ACCESS_KEY_ID = "AKIAJXSES3NWHCU7TNIQ"
    AWS_SECRET_ACCESS_KEY = "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"

    #AWS_ACCESS_KEY_ID = "AKIAJL6J66PRRBMABHFQ"
    #AWS_SECRET_ACCESS_KEY = "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"

    # Dynamodb access for kvstore/keyframe
    DYNAMODB_AWS_REGION = "us-west-2"
    KV_STORE_S3_BUCKET = "ml-dev"
    KV_STORE_DYNAMODB_TABLE = "client_bots_kvstore_dev"

    SLACK_BOT_ID = "U3KC79GGH"
    SLACK_VERIFICATION_TOKEN = "Avr8oGeFjTX2PJdJ1NKurE6V"

    #MYRA_API_HOSTNAME = "api.dev.myralabs.com"
    MYRA_API_HOSTNAME = os.getenv("MYRA_API_HOSTNAME", "api.dev.myralabs.com")
    MYRA_INFERENCE_PROXY_LB = os.getenv(
        "MYRA_INFERENCE_PROXY_LB",
        "inference.dev.myralabs.com")
    MYRA_INFERENCE_PROXY_LB_PORT = os.getenv(
        "MYRA_INFERENCE_PROXY_LB_PORT", 81)

    MYRA_SEARCH_SERVER = os.getenv("MYRA_SEARCH_SERVER", "search.dev.myralabs.com")
    MYRA_SEARCH_ENDPOINT = os.getenv("MYRA_SEARCH_ENDPOINT", "nlp_search")

    SEND_EMAIL = distutils.util.strtobool(os.getenv("MYRA_SEND_EMAIL", "true"))
    SEND_EMAIL_AUTH_KEY = "key-82392a82671aef14bc88bdf73977182d"

    # Test page access token.
    FB_PAGE_ACCESS_TOKEN = "EAANkHwib2HcBAAZAEVORAemInZAOAlIn6BzP4nmfUKxCe562rRQnZBxCHgZAaaxYskZBciitSipgUfQccKu5oCc1ZCGK6JxeXm0j5rBhI7ZBYl86gqAvEHn7aAeZA3C3x1BlczEqLwnVpKc0KXh7NwKBE85Jk1ONG36mzMetRbj93"

    DB_CONN_STRING = "dbname='myra_db_dev' user='myraadmin' host='myra-db-dev.cihwyaszqq2o.us-west-2.rds.amazonaws.com' password='RZ4KvefI3f9e'"

    INTERCOM_SIGNUP_MSG = """
Thanks for installing Myra. If you have an account with us, please enter your credentials here. If not, please contact sales@myralabs.com for an account / go to myralabs.com/signup (https://myralabs.com/signup) to create a new one.
    """
    
class DevConfig(Config):
    pass

class TestConfig(DevConfig):
    pass

class ProdConfig(Config):
    KV_STORE_S3_BUCKET = "ml-prod"

    SLACK_BOT_ID = "A3Y82KUCE"
    SLACK_VERIFICATION_TOKEN = "BweHbKtg9sBuOXXi92dU3e4Z"

    #MYRA_API_HOSTNAME = os.getenv("MYRA_API_HOSTNAME", "api.myralabs.com")
    MYRA_API_HOSTNAME = "api.prod.myralabs.com"
    MYRA_INFERENCE_PROXY_LB = os.getenv(
        "MYRA_INFERENCE_PROXY_LB",
        "inference.prod.myralabs.com")
    MYRA_INFERENCE_PROXY_LB_PORT = os.getenv(
        "MYRA_INFERENCE_PROXY_LB_PORT", 81)

    MYRA_SEARCH_SERVER = os.getenv("MYRA_SEARCH_SERVER", "search.prod.myralabs.com")

    # This is IAM user dyndb-prod
    AWS_ACCESS_KEY_ID = "AKIAJACRM3ORXT3E6HVA"
    AWS_SECRET_ACCESS_KEY = "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"
    KV_STORE_DYNAMODB_TABLE = "client_bots_kvstore_prod"

    KINESIS_STREAM_PREFIX = os.getenv("KINESIS_STREAM_PREFIX","kf-events-prod")
    KINESIS_STREAM_NAME = "kf-events-prod"

    KF_EVENTS_S3_BUCKET = "ml-logs-prod"

    AWS_S3_PUBLIC_UPLOAD_ACCESS_KEY_ID = "AKIAJBSHFRRWUL6DHWGA"
    AWS_S3_PUBLIC_UPLOAD_SECRET_ACCESS_KEY = "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"
    AWS_S3_PUBLIC_UPLOAD_BUCKET = "ml-public-upload-prod"

    DB_CONN_STRING = "dbname='myra_db_prod' user='myraadmin' host='myra-db-main.cihwyaszqq2o.us-west-2.rds.amazonaws.com' password='RZ4KvefI3f9e'"


import os
import logging
import distutils
import distutils.util

log = logging.getLogger(__name__)

# Zappa creates 'STAGE' env var based on the deploy.
# 'zappa deploy dev' => STAGE=dev
# So STAGE overrides realm if it exists.
TMP_REALM = os.getenv("REALM", "dev")
REALM = os.getenv("STAGE", TMP_REALM)
log.info("REALM: %s", REALM)

def getConfig(realm=None):
    if not realm:
        realm = REALM
    log.debug("getConfig realm: %s", realm)
    if realm == "prod":
        return ProdConfig()
    elif realm == "dev":
        return Config()
    elif realm == "test":
        return TestConfig()
    else:
        raise "Unknown REALM: %s" % (realm,)

class Config(object):
    BOTSTATE_TTL_SECONDS = int(os.getenv("BOTSTATE_TTL_SECONDS", 60*60*6))  # 6 hours
    BOTSTATE_HISTORY_TTL_SECONDS = BOTSTATE_TTL_SECONDS
    INTENT_SCORE_THRESHOLD = 0.7

    KINESIS_USER_ACCESS_KEY_ID = "AKIAII26HBVXJUNGKT5A"
    KINESIS_USER_SECRET_ACCESS_KEY = "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"
    KINESIS_AWS_REGION = "us-west-2"

    KINESIS_STREAM_PREFIX = os.getenv("KINESIS_STREAM_PREFIX","kf-events-dev")

    DYNAMODB_AWS_REGION = "us-west-2"
    KV_STORE_S3_BUCKET = "ml-dev"

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

    SEND_EMAIL = distutils.util.strtobool(os.getenv("MYRA_SEND_EMAIL", "true"))
    SEND_EMAIL_AUTH_KEY = "key-82392a82671aef14bc88bdf73977182d"

    # Test page access token.
    FB_PAGE_ACCESS_TOKEN = "EAANkHwib2HcBAAZAEVORAemInZAOAlIn6BzP4nmfUKxCe562rRQnZBxCHgZAaaxYskZBciitSipgUfQccKu5oCc1ZCGK6JxeXm0j5rBhI7ZBYl86gqAvEHn7aAeZA3C3x1BlczEqLwnVpKc0KXh7NwKBE85Jk1ONG36mzMetRbj93"

class DevConfig(Config):
    pass

class TestConfig(DevConfig):
    pass

class ProdConfig(Config):
    KV_STORE_S3_BUCKET = "ml-prod"

    SLACK_BOT_ID = "A3Y82KUCE"
    SLACK_VERIFICATION_TOKEN = "BweHbKtg9sBuOXXi92dU3e4Z"

    MYRA_API_HOSTNAME = os.getenv("MYRA_API_HOSTNAME", "api.myralabs.com")
    #MYRA_API_HOSTNAME = "api.prod.myralabs.com"

    # This is IAM user dyndb-prod
    AWS_ACCESS_KEY_ID = "AKIAJACRM3ORXT3E6HVA"
    AWS_SECRET_ACCESS_KEY = "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"
    KV_STORE_DYNAMODB_TABLE = "client_bots_kvstore_prod"

    KINESIS_STREAM_PREFIX = os.getenv("KINESIS_STREAM_PREFIX","kf-events-prod")

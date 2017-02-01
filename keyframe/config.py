import os

# Zappa creates 'STAGE' env var based on the deploy.
# 'zappa deploy dev' => STAGE=dev
# So use this as the realm here.
REALM = os.getenv("STAGE", "dev")

def getConfig(realm=None):
    if not realm:
        realm = REALM
    if realm == "prod":
        return ProdConfig()
    elif realm == "dev":
        return Config()
    elif realm == "test":
        return TestConfig()
    else:
        raise "Unknown REALM: %s" % (realm,)

class Config(object):
    INTENT_SCORE_THRESHOLD = 0.7

    DYNAMODB_AWS_REGION = "us-west-2"
    KV_STORE_S3_BUCKET = "ml-dev"

    AWS_ACCESS_KEY_ID = "AKIAJL6J66PRRBMABHFQ"
    AWS_SECRET_ACCESS_KEY = "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"

    SLACK_BOT_ID = "U3KC79GGH"
    SLACK_VERIFICATION_TOKEN = "Avr8oGeFjTX2PJdJ1NKurE6V"

    MYRA_API_HOSTNAME = "api.dev.myralabs.com"

    # Test page access token.
    FB_PAGE_ACCESS_TOKEN = "EAANkHwib2HcBAAZAEVORAemInZAOAlIn6BzP4nmfUKxCe562rRQnZBxCHgZAaaxYskZBciitSipgUfQccKu5oCc1ZCGK6JxeXm0j5rBhI7ZBYl86gqAvEHn7aAeZA3C3x1BlczEqLwnVpKc0KXh7NwKBE85Jk1ONG36mzMetRbj93"

class DevConfig(Config):
    pass

class TestConfig(DevConfig):
    pass

class ProdConfig(Config):
    KV_STORE_S3_BUCKET = "ml-prod"

    AWS_ACCESS_KEY_ID = "AKIAJL6J66PRRBMABHFQ"
    AWS_SECRET_ACCESS_KEY = "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"

    SLACK_BOT_ID = "A3Y82KUCE"
    SLACK_VERIFICATION_TOKEN = "BweHbKtg9sBuOXXi92dU3e4Z"

    MYRA_API_HOSTNAME = "api.prod.myralabs.com"

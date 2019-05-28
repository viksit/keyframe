from keyframe import store_api
from keyframe import bot_stores

def getIntercomAgentDeploymentMeta(appId, kvStore):
    ads = bot_stores.AgentDeploymentStore(kvStore) # =getKVStore()
    agentDeploymentMeta = ads.getJsonSpec(appId, "intercom_msg")
    return agentDeploymentMeta


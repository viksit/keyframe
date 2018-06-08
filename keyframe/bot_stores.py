from __future__ import absolute_import
import json
import logging

from . import store_api

log = logging.getLogger(__name__)

"""
Agent Deployment Store

For Slack:
    key:
        channelname.teamId

    dynamodbstore = {
          slack.T06SXL7GV = {
              "team_id": "T06SXL7GV",
                "bot_token": "xoxb-121415322561-hkR3eLghiCpVlgMZ5DrxExNh",
                "concierge_meta": {
                    "account_id": "BIRsNx4aBt9nNG6TmXudl",
                    "account_secret": "f947dee60657b7df99cceaecc80dd4d644a5e3bd",
                    "agent_id": "a7e4b5d749c74a8bb15e35a12a1bc5c6"
                }
            }
        }
"""

class AgentDeploymentStore(object):

    def __init__(self, kvStore):
        assert kvStore, "kvStore is required"
        self.kvStore = kvStore

    def _getKey(self, teamId, channel):
        k = "agentdeploy.%s.%s" % (channel, teamId)
        return k

    def getJsonSpec(self, teamId, channel):
        """
        Should return a python dict
        """
        k = self._getKey(teamId, channel)
        s = self.kvStore.get_json(k)
        if not s:
            return None
        return json.loads(s)

    def putJsonSpec(self, teamId, channel, jsonSpec):
        """
        Input is a python dict, and stores it as json
        """
        k = self._getKey(teamId, channel)
        self.kvStore.put_json(k, json.dumps(jsonSpec))


"""
BotMetaStore
{
  "botmeta.<acctid>.<agentid>" : {
     "jsonSpec": {},
   }
}
"""

def getBotMetaStore(kvStore=None, config=None):
    if not kvStore:
        kvStore = store_api.get_kv_store(config=config)  # will use defaults
    bms = BotMetaStore(kvStore)
    return bms

# Utility helpful function.
def getJsonSpec(accountId, agentId, kvStore=None, config=None):
    bms = getBotMetaStore(kvStore=kvStore, config=config)
    return bms.getJsonSpec(accountId, agentId)

class BotMetaStore(object):

    def __init__(self, kvStore):
        assert kvStore, "kvStore is required"
        self.kvStore = kvStore

    def _botMetaKey(self, accountId, agentId):
        k = "botmeta.%s.%s" % (accountId, agentId)
        log.info("BotMetaStore._botMetaKey k: %s", k)
        return k

    def getJsonSpec(self, accountId, agentId):
        """
        Should return a python dict
        """
        log.info("BotMetaStore.getJsonSpec(%s)", locals())
        k = self._botMetaKey(accountId, agentId)
        js = self.kvStore.get_json(k)
        if not js:
            return None
        return json.loads(js)

    def putJsonSpec(self, accountId, agentId, jsonSpec):
        """
        Input is a python dict, and stores it as json
        """
        k = self._botMetaKey(accountId, agentId)
        self.kvStore.put_json(k, json.dumps(jsonSpec))

    

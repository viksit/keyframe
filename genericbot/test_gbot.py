"""
To run:
(keyframe1) ~/work/keyframe/tutorial/genericbot $ env REALM=dev rlwrap python test_gbot.py testscripts/dev
(keyframe1) ~/work/keyframe/tutorial/genericbot $ env REALM=prod rlwrap python test_gbot.py testscripts/prod
"""

import sys, os
import logging
import json

from keyframe import store_api
from keyframe import config
from genericbot import generic_cmdline

log = logging.getLogger("genericbot")

def _extract_ids(scriptFile):
    with open(scriptFile, "r") as f:
        for l in f:
            if l.startswith("@"):
                return json.loads(l[1:].strip())
    return None

if __name__ == "__main__":
    usage = "test_gbot.py <test-data-file>"
    assert len(sys.argv) > 1, usage
    
    logging.basicConfig()
    log.debug("debug log")
    log.info("info log")

    cfg = config.getConfig()
    kvStore = store_api.get_kv_store(
        # store_api.TYPE_LOCALFILE,
        store_api.TYPE_DYNAMODB,
        # store_api.TYPE_INMEMORY,
        cfg)

    scriptLocation = sys.argv[1]
    scriptFiles = []
    if os.path.isfile(scriptLocation):
        scriptFiles.append(scriptLocation)
    elif os.path.isdir(scriptLocation):
        for f in os.listdir(scriptLocation):
            if os.path.isfile(os.path.join(scriptLocation, f)):
                scriptFiles.append(os.path.join(scriptLocation, f))

    errors = {}
    total_errors = 0
    log.debug("scriptFiles: %s", scriptFiles)
    assert scriptFiles
    for scriptFile in scriptFiles:
        ids = _extract_ids(scriptFile)
        assert ids
        accountId = ids.get("account_id")
        accountSecret = ids.get("account_secret")
        agentId = ids.get("agent_id")
        assert (ids and accountId and accountSecret and agentId), "missing ids"

        c = generic_cmdline.ScriptHandler(
            config_json={},
            accountId=accountId, accountSecret=accountSecret,
            agentId=agentId, kvStore=kvStore, cfg=cfg)
        c.scriptFile(scriptFile=scriptFile)
        num_errors = c.executeScript()
        errors[scriptFile] = num_errors
        if num_errors > 0:
            log.error("num_errors: %s", num_errors)
        total_errors += num_errors

    if total_errors > 0:
        sys.exit(1)


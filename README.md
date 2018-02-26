# Keyframe

magic.

## Running generic bot locally (to receive requests from local myra api server most probably).
Make sure the userId and userSecret correspond to the agents that you will be accessing.

```
env GBOT_LOG_LEVEL=20 rlwrap python gbot.py  http db 3rxCO9rydbBIf3DOMb9lFh 4b94f2de6d6554a006099c963e586d47485f9b4d
```

You can also point gbot to call the local api server which can also point to a local inference proxy to debug.

```
env GBOT_LOG_LEVEL=20 MYRA_API_HOSTNAME="localhost:7097"  rlwrap python gbot.py  http db 3rxCO9rydbBIf3DOMb9lFh 4b94f2de6d6554a006099c963e586d47485f9b4d
```

To debug keyframe with a custom bot spec via a file, you can download the bot spec (via a button in the UI) and then point gbot to it - it will use this botspec regardless of what is in the http call.

```
env KEYFRAME_KV_STORE_TYPE=type-localfile GBOT_LOG_LEVEL=10 MYRA_API_HOSTNAME="localhost:7097" rlwrap python gbot.py  cmd file 3rxCO9rydbBIf3DOMb9lFh 4b94f2de6d6554a006099c963e586d47485f9b4d  /Users/nishant/Downloads/nishant-topics-test-2.keyframe-config_6.json 
```

### Zendesk

API Host: https://myralabsdemo.zendesk.com/ <br>
Auth: greg@myralabs.com:cpUV4X9R8lEvGeguAa86Qph2rtIeSsL10bdL7ouA <br>
Ticket body: {{transcript}} <br>
Response: An email has been sent and you will get a response asap. ticket url: {{ticket.agenturl}} <br>

## To debug most things

#### gbot/gbot.py
GenericBotHTTPAPI(generic_bot_api.GenericBotAPI)

##### GenericBotAPI
Contains the highest level wrapper that creates a channelClient,
creates a botAPI with that channelClient, calls handle on botAPI.

##### GenricBotHTTPAPI
Entry point for the HTTP service (/run_agent).
Functions to get the botSpec json from store.
calls GenericBotHTTPAPI.requestHandler with the event.
Contains getBot(), which creates the bot object (injecting into it
everything it needs like kvStore, configJson, api, other configs).

#### keyframe/bot_api.py

##### BotAPI
handleMsg: handles the incoming msg by creating the bot (calling getBot),
and calling process on the bot.


#### genericbot/generic_bot.py
##### GenericBot(keyframe.base.BaseBot)
Doesn't do much, except override createActionObject and calls
generic_action.GenericActionObject.createActionObject instead of its base class.

#### keyframe/base.py
##### BaseBot
###### process
Increments the botstate (this is for going back to previous state).
Calls handle (see below).

###### *handle*
This is the main logic loop of the bot.
Checks for botcmd and executes and returns if it is a botcmd.
Loops executing the right topics. This includes
* getting a start topic if required.
* dealing with topic transfer.
* continuing with an existing topic (botState.getWaiting())
* Calls createActionObject(topicId,..)
* Then calls processWrapper on the actionObject.

#### genericbot/generic_action.py
Contains two important functions.

##### GenericActionObject.slotFill[Conditional]
Main slotFill loop to traverse the slot graph and fill the slots.
Deal with the different types of slots, get the right slot type and call *fill*
on it. Depending on its return, loop to the next slot or exit.

##### GenericActionObject.createActionObject
Creates the actionObject from the json spec. A lot of code here, including an api call after evaluating if any of the slots require an api call.

### Code for slots is divided into generic_slot.py and slot_fill.py

#### genericbot/generic_slot.py
##### GenericHiddenSlot
* Overrides fill
##### GenericTransferSlot
* Overrides fill
##### GenericIntentModelSlot
* Does not override fill, but overrides two other functions to do with extracting from utterance.
##### GenericInfoSlot
* Overrides fill
##### GenericActionSlot
* Overrides fill. Contains all code for different actions - webhook, email, zendesk.



## Making calls to lambda

Replace actual address with the relevant keyframe lambda address and realm [dev|prod|test].

`curl -v -H "Content-Type: application/json" --request POST "https://rrn3luxtdj.execute-api.us-west-2.amazonaws.com:443/test/run_agent?account_id=3rxCO9rydbBIf3DOMb9lFh&account_secret=4b94f2de6d6554a006099c963e586d47485f9b4d&agent_id=e7704006fc5542acb04e3522fa64f53a" -d '{"text": "hello", "rid": "d15bf744-06ea-49ec-ab1b-27e252f18b1a", "user_id": "console_3rxCO9rydbBIf3DOMb9lFh"}'
`
## Logging

### Keyframe package
keyframe using logging. It does not set up any specific loggers as recommended
by the logging community. It also uses loggers with "keyframe.*" in the hierarchy.

To modify logging for the library, create the appropriate logger for "keyframe".
This will be inherited by all the modules.

### To debug keyframe
> env KEYFRAME_LOG_LEVEL=10 python <script.py>

# GenericBot

## Logging
Uses loggers with "genericbot.*" hierarchy.

# GBOT

See gbot.py. Logging is set by GBOT_LOG_LEVEL env var for genericbot, keyframe and pymyra. But you can comment out a couple of lines inside gbot.py and not set loglevel for keyframe and/or keyframe and set those independently with their own env vars or explicitly in the code for debugging.



## Uploading a bot spec to dynamodb

    import keyframe.store_api as store_api
    import json
    import keyframe.config

    config = keyframe.config.getConfig()  # keyframe.config.getConfig(realm='prod') for prod
    kvStore = store_api.get_kv_store(store_api.TYPE_DYNAMODB, config)
    # k = 'botmeta.<accountId>.<agentId>'
    k = 'botmeta.3rxCO9rydbBIf3DOMb9lFh.94e0d0a482664965abc63e13638636e2'
    s = open('/Users/nishant/work/keyframe/genericbot/example-configs/lyft_test.json','r').read()
    j = json.loads(s)
    x = json.dumps(j)
    kvStore.put_json(k, x)

## Downloading a bot spec from dynamodb

    import keyframe.store_api as store_api
    import json
    import keyframe.config

    config = keyframe.config.getConfig()  # keyframe.config.getConfig(realm='prod') for prod
    kvStore = store_api.get_kv_store(store_api.TYPE_DYNAMODB, config)
    # k = 'botmeta.<accountId>.<agentId>'
    k = 'botmeta.3rxCO9rydbBIf3DOMb9lFh.94e0d0a482664965abc63e13638636e2'
    x = kvStore.get_json(k)
    botSpec = json.loads(x)
    

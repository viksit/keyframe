# Keyframe

## DEBUG

#### Find json spec for an agent
https://keyframe.prod.myralabs.com/botspec?account_id=7BbmKJgxsMKRuAcBjNA1Zo&agent_id=ff5d6b516c1142f09aef7c3df865987f

#### Get errors from lambda logs
```
~/work/keyframe $ date --utc -d 20190225 +%s
1551052800
~/work/keyframe $ date --utc -d 20190226 +%s
1551139200

~/work/keyframe $ aws logs filter-log-events --log-group-name "/aws/lambda/keyframe-prod" --start-time 1551052800000 --end-time 1551139200000 --filter-pattern "GOT EXCEPTION" > /mnt/tmp/keyframe.exceptions.20190225
```

## Intercom messenger integration

#### Configurable options (from agent):
intercomMessengerAppTitle: Title of the intercom widget<br>
intercomMessengerHomeScreenWelcomeMessage: Welcome message on the intercom home screen.

#### Technical info:
Intercom app webhooks are set up on intercom. They are:
/v2/intercom/configure:
Called when user is adding the app to their intercom widget.
We configure our intercom integration by asking for the account_id and adding the mapping
from the intercom_app_id to the account_id.
Currently we check for the account_id having an agent for Intercom already configured. If an agent is not configured, all intercom webhook calls by the app will fail.

/v2/intercom/initialize: 
Called when a new user is to be shown the app. It seems to be cached so if this webhook
is changed, it may not have much effect. To get around this, we send back a 'LiveCanvas',
which is essentially a url that gets called every time (like initialize should have been...).
Note that we have to send back a LiveCanvas, *not* the contents of the endpoint below directly. (They will be cached and so we will not be able to change them.)
Currently we send back /v2/intercom/startinit, so effectively
/v2/intercom/initialize -> /v2/intercom/startinit.

/v2/intercom/startinit:
Sends back 2 buttons.
Button1: A submit that starts the native app. (/v2/intercom/submit)
Button2: A 'SheetsAction' which points to /widget_page which is a html page with our widget,
set to open at the start. By using the app_id, we get the IntercomAgentDeploymentMeta dict,
and then substitute in the page the accountId and agentId and our widget then start up.

/v2/intercom/submit:
Gets called for the native app, and we parse out the input and feed it in as a call to
/run_agent2. Not used for the non-native iframe widget.

## Testing intercom app integration

./start.sh to start local keyframe
./start_ngrok.sh to start ngrok tunnels that are set up as webhooks in intercom app.

Go to myra-widget.
npm start

localhost:8080/intercom_msg.html

use the sample integration there.

### On Intercom web site
Login
Click on 'App Store' (the icon with 3 squares and a +).
There should be a link to 'build your own app' at the top. Click it.
That should open up this link: https://app.intercom.com/a/apps/<app-id>/developer-hub
(In case going to this link directly does not work..)




## After changes on 07 June 2018, run like this:
```
(keyframe1) ~/work/keyframe-2/keyframe $ #env MYRA_SEARCH_SERVER="localhost:7096" KEYFRAME_EVENT_WRITER_TYPE=file MYRA_ENV=dev MYRA_INFERENCE_PROXY_LB="localhost" MYRA_INFERENCE_PROXY_LB_PORT=7096 MYRA_LOG=info rlwrap python -m gbot.gbot http db  2>&1 | tee /tmp/gbot.log.$(date +%s)
```

magic.

## Running generic bot locally (to receive requests from local myra api server most probably).
Make sure the userId and userSecret correspond to the agents that you will be accessing.

```
# http for local widget
env GBOT_LOG_LEVEL=20 rlwrap python gbot.py  http db 3rxCO9rydbBIf3DOMb9lFh 4b94f2de6d6554a006099c963e586d47485f9b4d

# cmd
env GBOT_LOG_LEVEL=20 rlwrap python gbot.py  cmd db 3oPxV9oFXxzHYxuvpy56a9 f111cef48e1548be8d121f9649b368ebvio

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
    

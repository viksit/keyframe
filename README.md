# Keyframe

magic.

## Running generic bot locally (to receive requests from local myra api server most probably).
`
(keyframe1) ~/work/keyframe/gbot $ python gbot.py http db 2>&1 | tee /tmp/gbot.log.$(date +%s)
`

## To debug most things

keyframe/base.py:handle - this has the creation of the action object from the intent.
keyframe/actions.py:processWrapper - actually handles the user utterance.

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


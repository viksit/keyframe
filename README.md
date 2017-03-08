# Keyframe

magic.

## To debug most things

keyframe/base.py:handle - this has the creation of the action object from the intent.
keyframe/actions.py:processWrapper - actually handles the user utterance.

## Making calls to lambda

Replace actual address with the relevant keyframe lambda address and realm [dev|prod|test].

`curl -v -H "Content-Type: application/json" --request POST "https://rrn3luxtdj.execute-api.us-west-2.amazonaws.com:443/test/run_agent?account_id=3rxCO9rydbBIf3DOMb9lFh&account_secret=4b94f2de6d6554a006099c963e586d47485f9b4d&agent_id=e7704006fc5542acb04e3522fa64f53a" -d '{"text": "hello", "rid": "d15bf744-06ea-49ec-ab1b-27e252f18b1a", "user_id": "console_3rxCO9rydbBIf3DOMb9lFh"}'
`

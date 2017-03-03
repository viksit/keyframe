# Keyframe

magic.

## Logging

keyframe using logging. It does not set up any specific loggers as recommended
by the logging community. It also uses loggers with "keyframe.*" in the hierarchy.

To modify logging for the library, create the appropriate logger for "keyframe".
This will be inherited by all the modules.

### To debug keyframe
> env KEYFRAME_LOG_LEVEL=10 python <script.py>

# GenericBot

## Logging

See gbot.py. Logging is set by GBOT_LOG_LEVEL env var for genericbot, keyframe and pymyra. But you can comment out a couple of lines inside gbot.py and not set loglevel for keyframe and/or keyframe and set those independently with their own env vars or explicitly in the code for debugging.

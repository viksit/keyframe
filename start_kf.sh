# Start keyframe and connect to dev inference_proxy (for intent models and search).
# Also write events to kinesis vs local.
env KEYFRAME_EVENT_WRITER_TYPE=kinesis MYRA_ENV=dev MYRA_LOG=INFO python -m keyframe.gbot.gbot http db

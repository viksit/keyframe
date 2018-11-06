# Start keyframe to connect to connect to a local inference proxy (for intent models and search).
env MYRA_SEARCH_SERVER="localhost:7096" KEYFRAME_EVENT_WRITER_TYPE=file MYRA_ENV=dev MYRA_INFERENCE_PROXY_LB="localhost" MYRA_INFERENCE_PROXY_LB_PORT=7096 MYRA_LOG=DEBUG python -m keyframe.gbot.gbot http db

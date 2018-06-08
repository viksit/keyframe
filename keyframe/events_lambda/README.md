# How to deploy

 - ``zappa update [dev|prod]``
 - Go to AWS lambda
  - change the Configuration -> Handler to ``keyframe_event_handler.lambda_handler``.
  - Make sure in the Code -> Environment variables, the env var ``REALM`` is set correctly to ``[dev|prod]``.
  - Actions -> Publish New Version.

### NOTE: setting env vars in zappa config does not work in this case. Zappa wraps a call via the API Gateway and adds the environment variables through the wrapper. We're only using zappa as a convenient way to deploy. This is why the above steps are required.

## How to test

- Create some events via the [dev|prod] UI based chat widget.
- Check the events appear in the right place in s3.




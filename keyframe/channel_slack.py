# -*- coding: utf-8 -*-
"""
Slack integration contains two parts.

1) The flask application setup which allows you to install concierge into your slack system (via add to slack)

This requires /listening and oauth etc.
Should be handled at the level of the myra application.

The APIs should be supported here. This should be written into a slack deployment tutorial.

2) The second part of this to actually act on the end point once the API is live.
The latter is what this file does.

Assumption: Set up is already done and now we're just processing.


"""

import os
import message

from slackclient import SlackClient

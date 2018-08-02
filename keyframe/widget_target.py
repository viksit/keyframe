from __future__ import absolute_import
import sys, os
from os.path import join
import six.moves.urllib.parse
import logging
import re

from keyframe import config
from keyframe import store_api

# https://github.com/jessepollak/urlmatch
# uncomment if used - see check_urlmatch
#from urlmatch import urlmatch

log = logging.getLogger("__name__")

def _extractDomainAndPathFromUrl(url):
    log.debug("url: %s", url)
    p = six.moves.urllib.parse.urlparse(url)
    #domainPart = ".".join(p.netloc.rsplit('.', 2)[-2:])
    s = "%s%s" % (p.netloc, p.path)
    s = s.rstrip("/") #  + "/"
    # above will transform "http://help.wpengine.com/foo/bar/?baz=bat"
    # into "help.wpengine.com/foo/bar" which is what we want.
    log.debug("s: %s", s)
    return s

def validateWidgetTarget(kvStore, agentId, url):
    k = "widget_target.%s" % (agentId)
    widgetTargetConfig = kvStore.get_json(k)
    log.debug("found widgetTargetConfig: %s", widgetTargetConfig)
    return _evaluateWidgetTarget(widgetTargetConfig, url)

"""
Example widgetTargetConfig:
{'agent_enabled': True,
 'url_whitelist_enabled': True,
 'url_regex': ['support.myralabs.com', 'support.dev.myralabs.com'],
 'url_whitelist': ['www.foo.com/bar', 'www.foo.com/baz']
}
"""
def _evaluateWidgetTarget(widgetTargetConfig, url):
    if not widgetTargetConfig:
        return False
    if not widgetTargetConfig.get("agent_enabled"):
        return False
    if not widgetTargetConfig.get("url_whitelist_enabled"):
        return True
    if not url:
        log.info("url filter is enabled and no url specified.")
        return False
    urlAndPath = _extractDomainAndPathFromUrl(url)
    urlWhitelist = widgetTargetConfig.get("url_whitelist")
    # note that the whiteList is actually a dict for faster lookup.
    log.debug("looking at urlWhitelist")
    if urlWhitelist and urlAndPath in urlWhitelist:
        log.debug("found url in urlWhitelist")
        return True
    urlRegexList = widgetTargetConfig.get("url_regex")
    if not urlRegexList:
        return False
    for r in urlRegexList:
        if re.match(r, urlAndPath):
            log.debug("matched regex: %s", r)
            return True
    return False



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

log = logging.getLogger(__name__)

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

def getWidgetTargetConfig(kvStore, agentId):
    k = "widget_target.%s" % (agentId)
    widgetTargetConfig = kvStore.get_json(k)
    log.debug("found widgetTargetConfig: %s", widgetTargetConfig)
    return widgetTargetConfig


"""
Example widgetTargetConfig:
{'agent_enabled': True,
 'url_whitelist_enabled': True,
 'url_regex': ['support.myralabs.com', 'support.dev.myralabs.com'],
 'url_whitelist': ['www.foo.com/bar', 'www.foo.com/baz']
}
"""
def evaluateWidgetTarget(widgetTargetConfig, url):
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


"""
Example of widgetTargetConfig:
{
    "agent_enabled": true,
    "url_whitelist_enabled": true
    'url_regex': ['support.myralabs.com', 'support.dev.myralabs.com'],
    'url_whitelist': ['www.foo.com/bar', 'www.foo.com/baz'],
    "contextualCtaLookup": {
        "Context Name 1": {
            "cta_element": "CTA Element 1",
            "default_intent": "[topic=topic_1df1240009bf44078117d4705d250cd9]",
            "name": "Context Name 1",
            "render_fn": "render_function_1",
            "urls": [
                "www.wpengine.com/helppage1",
                "www.wpengine.com/dns1",
                "help.wpengine.com/dns2"
            ]
        }
    },
    "lookupContexts": {
        "help.wpengine.com/dns2": ["Context Name 1",],
        "www.wpengine.com/dns1": ["Context Name 1",],
        "www.wpengine.com/helppage1": ["Context Name 1",],
    },
}
"""
def getContextConfig(widgetTargetConfig, url):
    log.info("getContextConfig(cfg, url=%s)", url)
    cfg = widgetTargetConfig.get("contextualConfig")
    log.info("cfg: %s", cfg)
    if not cfg:
        return {"enabled": False, "contexts": []}
    if not cfg.get("enabled", False):
        return {"enabled": False, "contexts": []}
    normalizedUrl = _extractDomainAndPathFromUrl(url)
    log.info("looking up normalizedUrl: %s in cfg", normalizedUrl)
    contextNames = cfg.get("lookupContexts", {}).get(normalizedUrl)
    log.info("got contextNames: %s", contextNames)
    if not contextNames:
        return {"enabled": True, "contexts": []}
    contexts = []
    contextualCtaLookup = cfg.get("contextualCtaLookup", {})
    log.info("contextualCtaLookup: %s", contextualCtaLookup)
    myraUrlParam = None
    referrerParsed = six.moves.urllib.parse.urlparse(url)
    #log.info("referrerParsed: %s", referrerParsed)
    if referrerParsed.query:
        _tmp = six.moves.urllib.parse.parse_qs(referrerParsed.query)
        if _tmp.get("mwf_ap"):
            myraUrlParam = _tmp.get("mwf_ap")[0]
    log.info("myraUrlParam: %s", myraUrlParam)
    for cn in contextNames:
        contextCfg = contextualCtaLookup.get(cn)
        log.info("got contextCfg: %s", contextCfg)
        if contextCfg:
            contextCfg["autopopup"] = False
            if (contextCfg.get("autoPopupUrls")
                and contextCfg.get("autoPopupUrls").count(url)):
                log.info("autopopup=True as %s matched", url)
                contextCfg["autopopup"] = True
            if (myraUrlParam
                and contextCfg.get("popupUrlParams")
                and contextCfg.get("popupUrlParams").count(myraUrlParam)):
                contextCfg["autopopup"] = True
            contexts.append(contextCfg)
    return {
        "enabled": True,
        "contexts": contexts}

from __future__ import absolute_import
import logging
import re
import sys

import pymyra.api.client

log = logging.getLogger(__name__)

def getClasses(cls):
    allClasses = [cls.__getattribute__(cls, i) for i in cls.__dict__.keys() if i[:1] != '_']
    return allClasses

class BaseField(object):

    def __init__(self, **kwargs):
        log.debug("BaseField.__init__(%s)", kwargs)
        self.label = kwargs.get("label") # name
        self.field_type = re.sub(r"(.)([A-Z])", r"\1_\2", self.__class__.__name__).lower()
        # Only relevant for certain kinds of inherited classes of type APIIntent
        self.apiResult = None

    def field_eval_fn(self, **kwargs):
        """
        Must return {"result":bool, ...}
        """
        pass

    def __repr__(self):
        return "BaseField(label=%s, field_type=%s)" % (
            self.label, self.field_type)

# Intents

# TODO: What should the UnknownIntent do?
class UnknownIntent(BaseField):
    pass

class DefaultIntent(BaseField):

    _params = {}

    def __init__(self, **kwargs):
        log.debug("DefaultIntent.__init__(%s)", kwargs)
        super(DefaultIntent, self).__init__(**kwargs)

    def field_eval_fn(self, **kwargs):
        return {"result":True}

class RegexIntent(BaseField):

    _params = {}

    def __init__(self, **kwargs):
        super(RegexIntent, self).__init__(**kwargs)
        self.regex = kwargs.get("regex")
        assert self.regex is not None,\
            "Did you forget to initialize %s with a (.. regex=regexobj) argument?" % self.label

    def field_eval_fn(self, **kwargs):
        canonicalMsg = kwargs.get("canonicalMsg")
        r = bool(len(re.findall(self.regex, " " + canonicalMsg.text + " ")))
        return {"result":r}

class KeywordIntent(BaseField):

    _params = {}

    def __init__(self, **kwargs):
        super(KeywordIntent, self).__init__(**kwargs)
        self.keywords = set(kwargs.get("keywords"))
        assert self.keywords is not None,\
            "Did you forget to initialize %s with a (.. keyword=[list of kw]) argument?" % self.label

    def field_eval_fn(self, **kwargs):
        log.debug("keywordIntent.field_eval_fn(%s)", locals())
        canonicalMsg = kwargs.get("canonicalMsg")
        canonMsgTokenSet = set(canonicalMsg.text.split())
        log.debug("canonMsgTokenSet: %s", canonMsgTokenSet)
        log.debug("self.keywords: %s", self.keywords)
        ret = bool(set(canonMsgTokenSet.intersection(self.keywords)))
        log.debug("field_eval_fn returning %s", ret)
        return {"result":ret}

class APIIntent(BaseField):
    _params = {}

    def __init__(self, **kwargs):
        super(APIIntent, self).__init__(**kwargs)

    def field_eval_fn(self, **kwargs):
        log.debug("APIIntent.field_eval_fn(%s)", locals())
        apiResult = kwargs.get("apiResult")
        if not apiResult:
            myraAPI = kwargs.get("myraAPI")
            assert myraAPI is not None, "Have you registered an API object?"
            canonicalMsg = kwargs.get("canonicalMsg")
            urlParams = None
            if canonicalMsg.rid:
                urlParams = {"rid":canonicalMsg.rid}
            log.debug("calling myraAPI.get")
            try:
                self.apiResult = myraAPI.get(
                    canonicalMsg.text,
                    url_params=urlParams)
                log.debug("field_eval_fn.self.apiResult: %s", self.apiResult)
            except pymyra.api.client.InferenceClientError as ice:
                log.exception("Exception calling myra api")
                raise Exception("Exception calling myra api: %s" % (ice,))
        else:
            log.debug("apiResult was passed in")
            self.apiResult = apiResult
        intentStr = self.apiResult.intent.label
        log.debug("field_eval_fn intentStr: %s, returning: %s",
                  intentStr, (intentStr == self.label))
        r = (intentStr == self.label)
        return {"result":r, "score":self.apiResult.intent.score,
                "api_result":self.apiResult}

# Entities

# Extracting entities
ENTITY_DATE = "DATE"
ENTITY_TEXT = "text"

class BaseEntity(object):

    def __init__(self, **kwargs):
        self.needsAPICall = False
        self.label = kwargs.get("label") # name
        self.entityType = re.sub(r"(.)([A-Z])", r"\1_\2", self.__class__.__name__).lower()

    def entity_extract_fn(self, **kwargs):
        """
        Logic to extract something from a given sentence
        This is per entity.
        """
        pass

    def toJSON(self):
        return {
            "label": self.label,
            "entityType": self.entityType,
            "needsAPICall": self.needsAPICall
        }

    @classmethod
    def fromJSON(self, jsonObject):
        self.label = jsonObject.get("label")
        self.entityType = jsonObject.get("entityType")
        self.needsAPICall = jsonObject.get("needsAPICall")

class FreeTextEntity(BaseEntity):
    """
    Accepts anything as input
    """
    _params = {}

    def __init__(self, **kwargs):
        super(FreeTextEntity, self).__init__(**kwargs)

    def entity_extract_fn(self, **kwargs):
        text = kwargs.get("text", None)
        assert text is not None
        return text

class NumberEntity(BaseEntity):
    def __init__(self, **kwargs):
        super(NumberEntity, self).__init__(**kwargs)

    def entity_extract_fn(self, **kwargs):
        text = kwargs.get("text", None)
        assert text is not None
        text = text.strip()
        # hack to handle people entering 20% or $30 etc etc.
        # clearly non-ideal but will do for now.
        text = re.sub("[^0-9|.]", "", text)
        # We can't actually return a non-text because downstream assumes text.
        try:
            _tmp = float(text)
        except:
            log.info("cannot convert %s to a number", text)
            return None
        # We can't actually return a non-text because downstream assumes text
        # in various places.
        return text

class AttachmentsEntity(FreeTextEntity):
    def __init__(self, **kwargs):
        super(AttachmentsEntity, self).__init__(**kwargs)
    
class OptionsEntity(BaseEntity):
    def __init__(self, **kwargs):
        super(OptionsEntity, self).__init__(**kwargs)
        self.optionsList = kwargs.get("optionsList", None)

    def entity_extract_fn(self, **kwargs):
        log.debug("OptionsEntity.entity_extract_fn(%s)", locals())
        text = kwargs.get("text", None)
        assert self.optionsList is not None, "OptionsEntity does not have options"
        if not text:
            log.info("no text - cannot extract entity")
            return None
        if not self.optionsList:
            return None
        ol = [o.lower() for o in self.optionsList]
        if text.lower() not in ol:
            log.info("text (%s) not in optionsList (%s)",
                     text.lower(), ol)
            return None
        return text

class RegexEntity(BaseEntity):
    """
    Accepts anything as input
    """
    _params = {}

    def __init__(self, **kwargs):
        super(RegexEntity, self).__init__(**kwargs)
        self.regex = kwargs.get("regex", None)
        assert self.regex is not None, "Did you initialize %s with a regex=expression?" % self.label

    def entity_extract_fn(self, **kwargs):
        text = kwargs.get("text")
        return re.findall(self.regex, " " + text + " ")

class EmailRegexEntity(BaseEntity):
    """
    Accepts anything as input. Returns a email number (the first one),
    if found.
    """
    _params = {}

    def __init__(self, **kwargs):
        super(EmailRegexEntity, self).__init__(**kwargs)
        emailPattern = re.compile(r'[\w\-][\w\-\.\+]+@[\w\-][\w\-\.]+\.[a-zA-Z]{1,4}')
        self.regex = emailPattern
        assert self.regex is not None, "Did you initialize %s with a regex=expression?" % self.label
        self.entityType = "EMAIL"

    def entity_extract_fn(self, **kwargs):
        text = kwargs.get("text")
        groups = re.findall(self.regex, " " + text + " ")
        if len(groups):
            res = groups[0]
            # We should now have an email in here.
            return res
        return None


class PhoneRegexEntity(BaseEntity):
    """
    Accepts anything as input. Returns a phone number (the first one),
    if found.
    """
    _params = {}

    def __init__(self, **kwargs):
        super(PhoneRegexEntity, self).__init__(**kwargs)
        phonePattern = re.compile(r'''
        # don't match beginning of string, number can start anywhere
        (\d{3})     # area code is 3 digits (e.g. '800')
        \D*         # optional separator is any number of non-digits
        (\d{3})     # trunk is 3 digits (e.g. '555')
        \D*         # optional separator
        (\d{4})     # rest of number is 4 digits (e.g. '1212')
        \D*         # optional separator
        (\d*)       # extension is optional and can be any number of digits
        $           # end of string
        ''', re.VERBOSE)
        self.regex = phonePattern
        assert self.regex is not None, "Did you initialize %s with a regex=expression?" % self.label
        self.entityType = "PHONE"

    def entity_extract_fn(self, **kwargs):
        text = kwargs.get("text")
        groups = re.findall(self.regex, " " + text + " ")
        if len(groups):
            groups = [x for x in groups[0] if len(x)]
            # We should now have a phone number in here.
            # join it.
            res = "-".join(groups)
            return res
        return None

# Entities that we get from the API.
class APIEntity(BaseEntity):
    RESULT_KEY = None  # set to correct value in derived class

    def __init__(self, **kwargs):
        super(APIEntity, self).__init__(**kwargs)
        self.needsAPICall = True

    def entity_extract_fn(self, **kwargs):

        apiResult = kwargs.get("apiResult", None)
        assert apiResult is not None, "apiResult is None in extract_entity_fn"

        res = None
        e = apiResult.entities.entity_dict.get(self.RESULT_KEY, {})
        # We now store entity types inside of entity field definitions
        # So, we look at the entity object to see what kind of label it contains
        # Entity type was found
        if self.entityType in e:

            # TODO(viksit): the Myra API needs to change to have "text" in all entities.
            k = ENTITY_TEXT

            # TODO(viksit): special case for DATE. needs change in API.
            #if self.entityType == ENTITY_DATE:
            #    k = ENTITY_DATE.lower()

            # Extract the right value.
            tmp = [i.get(k) for i in e.get(self.entityType)]
            if len(tmp) > 0:
                log.info("\t(a) slot was filled in this sentence (%s)", tmp[0])
                res = tmp[0]
            else:
                log.info("\t(b) slot wasn't filled in this sentence")
        # The entity type wasnt found
        else:
            log.info("\t(c) slot wasn't filled in this sentence")

        # Finally.
        log.info("returning res: %s", res)
        return res

class BuiltInEntity(APIEntity):
    RESULT_KEY = "builtin"

class UserDefinedEntity(APIEntity):
    RESULT_KEY = "user_defined"

class PersonEntity(BuiltInEntity):
    _params = {}

    def __init__(self, **kwargs):
        super(PersonEntity, self).__init__(**kwargs)
        self.entityType = "PERSON"


class DateEntity(BuiltInEntity):
    _params = {}

    def __init__(self, **kwargs):
        super(DateEntity, self).__init__(**kwargs)
        self.entityType = "DATE"

class LocationEntity(BuiltInEntity):
    _params = {}

    def __init__(self, **kwargs):
        super(LocationEntity, self).__init__(**kwargs)
        self.entityType = "GPE"

class OrgEntity(BuiltInEntity):
    _params = {}

    def __init__(self, **kwargs):
        super(OrgEntity, self).__init__(**kwargs)
        self.entityType = "ORG"

# Models
class BaseModel(object):

    default = DefaultIntent(label="default")

    def __init__(self, **kwargs):
        assert self.label is not None
        self.name = re.sub(r"(.)([A-Z])", r"\1_\2", self.__class__.__name__).lower()

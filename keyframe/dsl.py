import logging
import re
import sys

log = logging.getLogger(__name__)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
logformat = "[%(levelname)1.1s %(asctime)s %(name)s] %(message)s"
formatter = logging.Formatter(logformat)
ch.setFormatter(formatter)
log.addHandler(ch)
log.setLevel(logging.DEBUG)
log.propagate = False

def getClasses(cls):
    allClasses = [cls.__getattribute__(cls, i) for i in cls.__dict__.keys() if i[:1] != '_']
    return allClasses

class BaseField(object):

    def __init__(self, **kwargs):
        self.label = kwargs.get("label") # name
        self.field_type = re.sub(r"(.)([A-Z])", r"\1_\2", self.__class__.__name__).lower()

    def field_eval_fn(self, **kwargs):
        """
        Must return bool (T/F)
        """
        pass


# Intents

class DefaultIntent(BaseField):

    _params = {}

    def __init__(self, **kwargs):
        super(DefaultIntent, self).__init__(**kwargs)

    def field_eval_fn(self, **kwargs):
        return True

class RegexIntent(BaseField):

    _params = {}

    def __init__(self, **kwargs):
        super(RegexIntent, self).__init__(**kwargs)
        self.regex = kwargs.get("regex")
        assert self.regex is not None,\
            "Did you forget to initialize %s with a (.. regex=regexobj) argument?" % self.label

    def field_eval_fn(self, **kwargs):
        canonicalMsg = kwargs.get("canonicalMsg")
        return bool(len(re.findall(self.regex, " " + canonicalMsg.text + " ")))

class KeywordIntent(BaseField):

    _params = {}

    def __init__(self, **kwargs):
        super(KeywordIntent, self).__init__(**kwargs)
        self.keywords = set(kwargs.get("keywords"))
        assert self.keywords is not None,\
            "Did you forget to initialize %s with a (.. keyword=[list of kw]) argument?" % self.label

    def field_eval_fn(self, **kwargs):
        canonicalMsg = kwargs.get("canonicalMsg")
        canonMsgTokenSet = set(canonicalMsg.text.split(" "))
        return bool(set(canonMsgTokenSet.intersection(self.keywords)))

class APIIntent(BaseField):
    _params = {}

    def __init__(self, **kwargs):
        super(APIIntent, self).__init__(**kwargs)

    def field_eval_fn(self, **kwargs):
        myraAPI = kwargs.get("myraAPI")
        canonicalMsg = kwargs.get("canonicalMsg")
        assert myraAPI is not None, "Have you registered an API object?"
        apiResult = myraAPI.get(canonicalMsg.text)
        intentStr = apiResult.intent.label
        return intentStr == self.label

# Entities

# Extracting entities
ENTITY_BUILTIN = "builtin"
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

# Entities that we get from the API.
class APIEntity(BaseEntity):

    def __init__(self, **kwargs):
        super(APIEntity, self).__init__(**kwargs)
        self.needsAPICall = True

    def entity_extract_fn(self, **kwargs):


        apiResult = kwargs.get("apiResult", None)
        assert apiResult is not None, "apiResult is None in extract_entity_fn"

        res = None
        e = apiResult.entities.entity_dict.get(ENTITY_BUILTIN, {})
        # We now store entity types inside of entity field definitions
        # So, we look at the entity object to see what kind of label it contains
        # Entity type was found
        print("self.entityType: ", self.entityType)
        if self.entityType in e:

            # TODO(viksit): the Myra API needs to change to have "text" in all entities.
            k = ENTITY_TEXT

            # TODO(viksit): special case for DATE. needs change in API.
            if self.entityType == ENTITY_DATE:
                k = ENTITY_DATE.lower()

            # Extract the right value.
            tmp = [i.get(k) for i in e.get(self.entityType)]
            print("tmp; ", tmp)
            if len(tmp) > 0:
                log.info("\t(a) slot was filled in this sentence")
                res = tmp[0]
            else:
                log.info("\t(b) slot wasn't filled in this sentence")
        # The entity type wasnt found
        else:
            log.info("\t(c) slot wasn't filled in this sentence")


        # Finally.
        return res

class PersonEntity(APIEntity):
    _params = {}

    def __init__(self, **kwargs):
        super(PersonEntity, self).__init__(**kwargs)
        self.entityType = "PERSON"


class DateEntity(APIEntity):
    _params = {}

    def __init__(self, **kwargs):
        super(DateEntity, self).__init__(**kwargs)
        self.entityType = "DATE"

class LocationEntity(APIEntity):
    _params = {}

    def __init__(self, **kwargs):
        super(LocationEntity, self).__init__(**kwargs)
        self.entityType = "GPE"

class OrgEntity(APIEntity):
    _params = {}

    def __init__(self, **kwargs):
        super(OrgEntity, self).__init__(**kwargs)
        self.entityType = "ORG"

# Models
class BaseModel(object):

    default = DefaultIntent()

    def __init__(self, **kwargs):
        assert self.label is not None
        self.name = re.sub(r"(.)([A-Z])", r"\1_\2", self.__class__.__name__).lower()

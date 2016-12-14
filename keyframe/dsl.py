import re

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

class KeywordIntent(BaseField):

    _params = {}

    def __init__(self, **kwargs):
        self.keywords = set(kwargs.get("keywords"))
        assert self.keywords is not None,\
            "Did you forget to initialize %s with a (.. keyword=[list of kw]) argument?" % self.label
        super(KeywordIntent, self).__init__(**kwargs)

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

class BaseModel(object):

    def __init__(self, **kwargs):
        assert self.label is not None
        self.name = re.sub(r"(.)([A-Z])", r"\1_\2", self.__class__.__name__).lower()

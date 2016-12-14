from keyframe.dsl import BaseModel, KeywordIntent, APIIntent, RegexIntent

class IntentModel(BaseModel):

    kw = ["hello", "hi", "yo"]
    regexobj = r"\D(\d{5})\D"

    greeting = KeywordIntent(label="f1", keywords=kw)
    create = APIIntent(label="create")
    cancel = APIIntent(label="cancel")
    fivedig = RegexIntent(label="fivedig", regex=regexobj)

    class Meta:
        description = "My fun intent model"

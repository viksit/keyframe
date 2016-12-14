from keyframe.dsl import BaseModel, KeywordIntent, APIIntent

class IntentModelv2(BaseModel):

    kw = ["hello", "hi", "yo"]

    greeting = KeywordIntent(label="f1", keywords=kw)
    create = APIIntent(label="create")
    cancel = APIIntent(label="cancel")

    class Meta:
        description = "My fun intent model"

from keyframe.dsl import BaseModel, KeywordIntent, APIIntent, RegexIntent
from keyframe.dsl import PersonEntity, DateEntity, OrgEntity, LocationEntity

class IntentModel(BaseModel):

    kw = ["hello", "hi", "yo"]
    regexobj = r"\D(\d{5})\D"

    greeting = KeywordIntent(label="f1", keywords=kw)
    create = APIIntent(label="create")
    cancel = APIIntent(label="cancel")
    fivedig = RegexIntent(label="fivedig", regex=regexobj)

    class Meta:
        description = "My fun intent model"

class EntityModel(BaseModel):

    person = PersonEntity(label="person")
    mydate = DateEntity(label="mydate")
    mycity = LocationEntity(label="mycity")
    mybank = OrgEntity(label="mybank")

    class Meta:
        description = "My even more fun entity model"

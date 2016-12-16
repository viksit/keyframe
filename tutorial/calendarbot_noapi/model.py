from keyframe.dsl import BaseModel, KeywordIntent, APIIntent, RegexIntent, PersonEntity, FreeTextEntity

class IntentModel(BaseModel):

    kw = ["hello", "hi", "yo"]
    regexobj = r"\D(\d{5})\D"

    greeting = KeywordIntent(label="f1", keywords=kw)
    create = KeywordIntent(label="create", keywords=["create"])
    cancel = KeywordIntent(label="cancel", keywords=["cancel"])
    fivedig = RegexIntent(label="fivedig", regex=regexobj)

    class Meta:
        description = "My fun intent model"

class EntityModel(BaseModel):

    user = FreeTextEntity(label="user")
    person = FreeTextEntity(label="person")
    mydate = FreeTextEntity(label="date")
    mycity = FreeTextEntity(label="city")
    mybank = FreeTextEntity(label="bank")

    class Meta:
        description = "My even more fun entity model"

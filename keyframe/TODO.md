# TODO

## deployments
- x lambda deployment via zappa
- x dev server (command line handler)
- live code reloading

## channels
- slack channel
- facebook channel


## keyframe binary
- keyframe binary

## dsl
- orm layer for models
- clean up, allow sync and train
- how to use this in the intents?



### questions for elasticsearch dsl
- what is mapping for?
- do we need it?

## slot fill
- take this and put into a separate class
- inject as necessary
- better algorithm for slot fill
- better entity recognition (spacy/trainable)
- integration with search index
- export this via a myra api


## state management
- use kv store
- export via a myra api to read/write from kv store backend


## misc
- github support



## myra updates
- use spacy latest version
- update entity model to do things even better

## Tests





# Notes and thoughts

## conversational flow

A bot is defined via a set of ActionObjects and Transitions between them. It takes one or more Utterances from a user and delivers a Response.

An Utterance is defined as a sentence that was sent to the bot.

An ActionObject is defined as a piece of code that achieves some Action and delivers a Response.

A Response is some information sent back to the user, either text, images or other media.

An Action is defined as calling out to an existing service, lookup or data that is independent from the bot logic.

Each Action can be associated with zero or more Slots.

A Slot is defined as a piece of data of a known Type.

A Type is defined as a real world object that is referred to in a sentence.

A bot can be in two states - Waiting or Processing.

Waiting is when the bot is doing nothing in the foreground.

Processing is when an ActionObject is executing.

A Transition is defined as one of,
- going from Waiting into Processing
- Processing one ActionObject to Processing another ActionObject
- Processing to Waiting

Each Transition is controlled by one or more of the following,

- Incoming user Utterance
- Output of an existing ActionObject
- History of user Utterances
- History of agent Responses
- Global state for that user

Global state is defined as a set of keys and values that store the most recent information about the user's ask and the bot's Response, including Responses and results of external Actions.

A transition function T is defined in the context of another function F such as,

```
T(state1, state2) = F(Incoming user utterance, output of existing ActionObject, History of user Utterances, Global State)
```

A Transition function in v0.2 of Keyframe is defined as,

```
T(state1, state2) = F_I(Incoming user utterance)
```

where F_I is an intent classification function.







## ORM API for models

```
delete:
http://localhost:7091/api/internal/delete_model_for_user?model_id=8446b802da8749ed86020c47b70a1096&user_id=3oPxV9oFXxzHYxuvpy56a9
{
  "message": "User Model has been deleted."
}


get
http://localhost:7091/api/internal/get_models_for_user?user_id=3oPxV9oFXxzHYxuvpy56a9
{
  "models": [
    {
      "display_training_status": "ready",
      "is_deployed": true,
      "model_data": {
        "arch_json": [
          {
            "customName": "horoscope_signs",
            "dataFileId": "0ce2898045b6449c900c768e1a1336ff",
            "dataFileName": "horoscope_signs.csv",
            "dataFilePath": "s3://ml-dev/data/files/0ce2898045b6449c900c768e1a1336ff",
            "id": "bb4426515cd54421b8c76f52584ea65b",
            "type": "DictionaryMatcher"
          },
          {
            "customName": "horoscope_time_periods",
            "dataFileId": "da973db1061d40e6b3e092e57396865f",
            "dataFileName": "horoscope_time_periods.csv",
            "dataFilePath": "s3://ml-dev/data/files/da973db1061d40e6b3e092e57396865f",
            "id": "8b380bfd7160437383f6b653d89b1ff0",
            "type": "DictionaryMatcher"
          },
          {
            "customName": "self_reference",
            "dataFileId": "aaa637479a434ac3a24c820d19e1b96d",
            "dataFileName": "self_reference.csv",
            "dataFilePath": "s3://ml-dev/data/files/aaa637479a434ac3a24c820d19e1b96d",
            "id": "ab4c7d3ef3c84aa28a1c74504e520818",
            "type": "DictionaryMatcher"
          }
        ],
        "test_file_id": null,
        "train_file_id": null,
        "validate_file_id": null
      },
      "model_id": "eb3381f003454ff6811dc4b21957f047",
      "model_name": "r29-1",
      "model_type": "entity",
      "model_user_id": "3oPxV9oFXxzHYxuvpy56a9",
      "ownership": "editable",
      "test_data": null,
      "test_file_name": null,
      "train_data": null,
      "train_file_name": null,
      "training_status": "done",
      "validate_data": null,
      "validate_file_name": null
    },
  ]
}


create
http://localhost:7091/api/internal/create_model_for_user?model_code=lstm&model_name=foobar&model_type=intent&user_id=3oPxV9oFXxzHYxuvpy56a9
{
  "message": "model created",
  "model_id": "m-lstm-d452a47b4947f889057eb9f10"
}


post/validate
http://localhost:7091/api/internal/validate_intent_put_data_file
{"message":"Uploaded file","result":{"file_id":"dcc9e7e486554ddf9aeee8acd76304bd","file_name":"botv2_test.tsv","file_path":"s3://ml-dev/data/files/dcc9e7e486554ddf9aeee8acd76304bd"}}

Post/validate
http://localhost:7091/api/internal/validate_intent_put_data_file
{"message":"Uploaded file","result":{"file_id":"d9aa1b576b624de5ac66f92cc42c6340","file_name":"botv2_train.tsv","file_path":"s3://ml-dev/data/files/d9aa1b576b624de5ac66f92cc42c6340"}}


# train model

http://localhost:7091/api/internal/train_model_for_user?batch_size=50&learning_rate=0.001&model_id=m-lstm-d452a47b4947f889057eb9f10&model_type=intent&nb_epoch=25&user_id=3oPxV9oFXxzHYxuvpy56a9

{
  "result": {
    "jobid": "1f8e79550ba140d0b34e70d38c9004d1",
    "message": "Training job created successfully"
  }
}


```


# DSL

- inspiration: elastic search dsl
- django orm

```python

from keyframe import intents, entities, agents

class CalendarIntentModel(intents.Model):

  mykeywords = ["foo", "bar", "baz"]
  myregex = r"foo(.)+*"
  create = intents.StatisticalIntent()
  cancel = intents.StatisticalIntent()
  foo = intents.RegexIntent(myregex)
  bar = intents.KeywordIntent(mykeywords)

  class Meta:
    modelName = "calendar intent"
    description = "foo"
    trainFile = ".."
    testFile = ".."


class CalendarEntityModel(entities.Model):

  mydict = ["foo", "bar", "baz"]

  # allow files or simply read them here

  myregex = r"foo(.)+*"

  foo = intents.RegexEntity(myregex)
  bar = intents.DictionaryEntity(mydict)

  class Meta:
    modelName = "calendar entities"
    description = "foo"



class CalendarAgent(agents.Agent):
  prodIntent = ..
  prodEntity = ..

```

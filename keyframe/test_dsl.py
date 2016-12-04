from __future__ import print_function

from dsl.field import Field, Text, APIIntent, KeywordIntent, RegexIntent
from dsl.utils import DslBase, ObjectBase, AttrDict
from dsl.doc import IntentModel





"""
# connections.create_connection(hosts=['localhost'])
# connections.get_connection().get_model(id='')



- Create an agent

- an intent model
+ save, train
- get id back
- save locally

- Each person only has one intent model, entity model and agent
- Agent is deployed via slack, web or facebook
- Agent code is stored on github and deployed to lambda

- Lets build the myra bot using this API.
- What are the intents?

greetings, search

In the intent model, we simply use the myintentmodel class to store mappings

config.py
---------
class MyraBotIntentModel():
    greetings = APIIntent()
    search = APIIntent()

    class Meta:
       test_file = ..
       train_file = ..
       model_name= "foo"
       description = "bar"

class MyraBotEntityModel():
    myfriend = PersonEntity()
    mydate = DateEntity()
    city = GPEEntity()



MyraBotIntentModel.init()
MyraBotEntityModel.init()
mi = MyraBotIntentModel()
mi.save()
mi.train()

me = MyraBotEntityModel()
me.save()
me.train()

mi.status()
me.status()

MyraAgent = BaseAgentv2(api=api)

# What this does is

views.py
--------
# In a configuration file
# IAM keys
# Myra keys

agent = BaseAgent(api=api)

@agent.intent(myintentmodel.create)
def foo(ActionObject):

  class myslot(Slot):
    entity_type = myentitymodel.myfriend
    prompt = lambda x: "Whats your name?"

  ..


  def process():
   ..
   ..



class MyCmdlineHandler(..):
  def init():
   ..
   ..


- an entity model

* save these

"""

class MyIntentModel(IntentModel):
    create = APIIntent()
    cancel = APIIntent()
    kwtest = KeywordIntent()
    retest = RegexIntent()

    class Meta:
        index = "foo"
        model_name = "calendar intent"
        description = "foo"
        train_file = "/Users/viksit/work/myra/myra/v2/ml/data/datasets/intent/calendar/botv2_train.tsv"
        test_file = "/Users/viksit/work/myra/myra/v2/ml/data/datasets/intent/calendar/botv2_test.tsv"

MyIntentModel.init()
i = MyIntentModel()
print("meta >>", i.meta)
print("udf >>", i.udf)
i.save()
i.train()

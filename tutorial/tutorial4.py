from __future__ import print_function
from os.path import expanduser, join

from pymyra.api import client

from keyframe.main import BaseBot, Actions, BotCmdLineHandler,\
    ActionObject, BaseBotv2, Slot
from keyframe import channel_client
from keyframe import messages
from keyframe import config

########### New code ####################

"""

keyframe initapp

# creates a bot.py and a models.py as well as a config.py

#define the models.py

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





# then

# set up myra key somewhere

keyframe sync intents, entities
keyframe train intents
keyframe test



"""








############## Tutorial code ####################

# Create an API object to inject into our bot
apicfg = {
    "account_id": "1so4xiiNq29ElrbiONSsrS",
    "account_secret": "a33efcebdc44f243aac4bfcf7bbcc24c29c90587"
}
# Intent and entity models that we're using
INTENT_MODEL_ID = "0dfb5f1fe1c54466bd31503cc4dd82e4"

# Establish a global API connection
api = client.connect(apicfg)
api.set_intent_model(INTENT_MODEL_ID)


"""

slots:
- person
- date

set up a meeting with jack
sure. for when?
tomorrow at 10am


set up a meeting
sure. with whom?
john
and when?
tomorrow




"""


# What do you want to do?
# build a calendar bot

# what should this bot do?
# create a meeting, cancel a meeting and modify a meeting.
# it should connect to google calendar and then do something with it.


# TODO(viksit): support classes and function decorators so that quick start can be easy.

bot = BaseBotv2(api=api)

# Actions
@bot.intent("create")
class CreateIntentActionObject(ActionObject):

    @bot.slot("create", ["person", "optional", "PERSON"])
    class PersonSlot(Slot):

        def prompt(self):
            return "who do you want to set up the meeting with?"

    @bot.slot("create", ["time", "optional", "DATE"])
    class PersonSlot(Slot):

        def prompt(self):
            return "and when?"


    @bot.slot("create", ["city", "optional", "GPE"])
    class CitySlot(Slot):

        def prompt(self):
            return "which city do you want to meet in?"


    @bot.slot("create", ["bank", "optional", "ORG"])
    class CitySlot(Slot):

        def prompt(self):
            return "which bank do you want to meet at?"


    # Intent functions
    def process(self):

        # At this point, any slots should be filled up.
        for slot in self.slots:
            print("(process) slot: ", slot.entityType, slot.filled, slot.value)

        # Process the response
        message = "Sure, I'll create the meeting for you"
        #resp = _returnResponse(e, message)
        resp = message

        # Send it back on this channel
        responseType = self.messages.ResponseElement.RESPONSE_TYPE_RESPONSE
        cr = self.messages.createTextResponse(self.canonicalMsg,
                                              resp,
                                              responseType)
        self.channelClient.sendResponse(cr)


@bot.intent("cancel")
class CancelIntentActionObject(ActionObject):

    def process(self):
        # Process the response
        #e = self.apiResult.entities.entity_dict.get("builtin", {})
        message = "Sure, I'll cancel the meeting for you"
        #resp = _returnResponse(e, message)
        resp = message
        # Send it back on this channel
        responseType = self.messages.ResponseElement.RESPONSE_TYPE_RESPONSE
        cr = self.messages.createTextResponse(self.canonicalMsg,
                                              resp,
                                              responseType)
        self.channelClient.sendResponse(cr)


class CalendarCmdlineHandler(BotCmdLineHandler):

    def init(self):

        # channel configuration
        cf = config.Config()
        channelClient = channel_client.getChannelClient(
            channel=messages.CHANNEL_CMDLINE,
            requestType=None,
            config=cf)

        self.bot = bot
        bot.setChannelClient(channelClient)

if __name__ == "__main__":
    c = CalendarCmdlineHandler()
    c.begin()

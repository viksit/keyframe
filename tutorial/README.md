# Zero to bot in 10 minutes

## Overview

Myra’s APIs are the best way to build natural language understanding into your applications. They provide tools to identify user intent and extract key data like names, cities, numbers, and custom-defined categories.

In this tutorial, we'll build a straightforward and state-of-the-art conversational bot that will produce results like this:

```bash

> cancel my meeting with Jane tomorrow at 9pm
>>  Sure, I'll cancel the meeting for you with Jane at Mon, 17 Oct 2016 21:00:00 GMT.

> create a meeting with Jane and Joe next saturday at 17:00 hours
>>  I can help create a meeting for you with Jane and Joe at Sat, 22 Oct 2016 17:00:00 GMT.

```

## Step 1: Install the SDK

`pymyra` provides access to the Myra RESTful APIs. It currently supports `python 2.7`.

Using `pip`:
```bash
pip install python-myra
```

Or from source:
```bash
git clone https://github.com/myralabs/python-myra
cd python-myra
pip install .
```

This will also install a sample configuration file into the following path `$HOME/.pymyra/settings.conf`.

## Step 2: Configure the SDK with your API credentials

- Register at http://api.myralabs.com/register
- When your account is opened, you'll receive an email with a link to the dashboard. 
- Log in to the dashboard and note the `account_id` and `account_secret`. Add those values into the appropriate places in the configuration file at`$HOME/.pymyra/settings.conf`.


## Step 3: Interact with CalendarBot

In the `python-myra` source directory, go to `tutorial/` and run `python tutorial.py`.

Meet CalendarBot! Ask it a question about creating or cancelling meetings.

```bash

python tutorial.py

calendar_bot>>  Welcome to calendar bot! I can help you create and cancel meetings. Try 'set up a meeting with Jane' or 'cancel my last meeting' to get started.

> cancel Jane's meeting with me tomorrow at 9pm
calendar_bot>>  Sure, I'll cancel the meeting for you with Jane at Mon, 17 Oct 2016 21:00:00 GMT.

> create a meeting with Jane and Joe next saturday at 17:00 hours
calendar_bot>>  I can help create a meeting for you with Jane and Joe at Sat, 22 Oct 2016 17:00:00 GMT.

```

## Step 4: Learn how CalendarBot is built

CalendarBot is built to understand questions about creating and cancelling calendar entries. Later, we'll add the ability to modify entries. (CalendarBot doesn't actually connect to a calendaring service, sorry!)

This tutorial ships with two sets of data files in the `tutorial/data` directory - `botv1` and `botv2`. Each directory contains two files - a training set and a testing set. A demo model for calendar queries has already been created for you by default using the `botv1/` dataset, and it's ID is `...`. [TODO: Greg]. This is what tutorial.py uses when you start.

Over the course of this tutorial, we'll walk you through extending the calendar bot to support one more piece of functionality - that of being able to modify existing calendar entries, by creating a model on Myra using the data in `botv2`, and extending tutorial.py in the right places.


Let's do a quick walkthrough of the code in `tutorial.py`.

`pymyra.api` contains the `client` module which we use to connect to the Myra API as described in the README which ships with the library.

```python
from pymyra.api import client

# Create the API config object from a configuration file
# This gets the config from /Users/<username>/.myra/settings.conf

CONF_FILE = join(expanduser('~'), '.pymyra', 'settings.conf')
config = client.get_config(CONF_FILE)

INTENT_MODEL_ID = "27c71fe414984927a32ff4d6684e0a73"

# Establish a global API connection
api = client.connect(config)
api.set_intent_model(INTENT_MODEL_ID)
```


If you now examine the `__main__` block, we initialize some bootstrap code which allows us to set up a command line interaction with our soon to be active bot.

```python

if __name__ == "__main__":
    # Initialize the calendar bot class
    bot = CalendarBot()

    # Start a simple command line handler to process incoming messages
    # and return a response
    c = client.CmdLineHandler(bot)
    c.begin(startMessage=bot.welcome_message,
      botName="calendar_bot")

```

Let's step through how we implement `CalendarBot`.

The bot has a `process()` function which takes in a user input (in this case from the terminal), invokes the Myra API on it via `api.get(user_input)`, and then passes this to the action handler function. The result from this call is then printed out on the terminal.

```python

result = api.get(user_input)
message = self.actions.handle(result=result)
print("calendar_bot>> ", message)

```

The last part of this file is the `Actions` class. This contains a simple mapping of intents to action handlers. For instance, if the bot detects that the user is asking to create a meeting, it'll invoke the `create_handler()` function.

What's left then is to simply define each handler function. Here's the code for the `cancel_handler` function.

```python
 def cancel_handler(self, **kwargs):
        api_result = kwargs.get("result")
        e = api_result.entities.entity_dict.get("builtin", {})
        message = "Sure, I'll cancel the meeting for you"
        if "PERSON" in e:
            person = [i.get("text") for i in e.get("PERSON")]
            person_text = ""
            if len(person) > 1:
                person_text = " and ".join(person)
            else:
                person_text = person[0]
            message += " with %s" % person_text

        if "DATE" in e:
            tm = [i.get("date") for i in e.get("DATE")]
            tm_text = ""
            if len(tm) >= 1:
                tm_text = tm[0]
            message += " at %s." % (tm_text)
        return message
```

The function gets the result of the Myra API, and fetches the detected entities into `e`. If it finds a mention of a person and a time, it responds with a simple static message constructed appropriately.



## Step 5: Extend CalendarBot to handle meeting modifications


- Train a new model on Myra using `data/botv2`.
- Change the intent model ID with the new ID

- Create a new entry in `self.intent_map` in the `Actions` class
```python
{
..,
..,
"modify": self.modify_handler
}
```

- Define a new function called `modify_handler` in the `Actions` class.

```python
 def modify_handler(self, **kwargs):
        api_result = kwargs.get("result")
        e = api_result.entities.entity_dict.get("builtin", {})
        message = "Sure, I can modify the meeting for you"
        if "PERSON" in e:
            person = [i.get("text") for i in e.get("PERSON")]
            person_text = ""
            if len(person) > 1:
                person_text = " and ".join(person)
            else:
                person_text = person[0]
            message += " with %s" % person_text

        if "DATE" in e:
            tm = [i.get("date") for i in e.get("DATE")]
            tm_text = ""
            if len(tm) >= 1:
                tm_text = tm[0]
            message += " at %s." % (tm_text)
        return message

```

Run `tutorial.py` again and try with the following sentence,

```
# Example here
```

## Next steps

TBD: [Greg]

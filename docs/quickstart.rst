Python-Myra Quick Start
================================

Myra's natural language APIs are the best way to build natural language understanding into your applications. With our tools, you can identify user intent and extract entities like names, cities, numbers and others.

This document will review setting up Myra's dashboards and using our built-in demo models to extract structured data from natural language.

If you've already signed up and downloaded an API key, you can:

- Install the SDK
- Use the demo models

Sign up
-------

- Go to http://api.myralabs.com/register and complete the form.
- You'll receive a confirmation email with an activation link.
- Click the link to complete sign up and log into the dashboard.


Create an API key pair
----------------------

In order to use the Myra API, you'll need to create an API Key. To get one, follow these steps,

- Step 1
- Step 2

- Screenshot

.. seealso:: This is a simple **seealso** note. Other inline directive may be included (e.g., math :math:`\alpha`) but not al of them.

.. todo:: Download settings from the dashboard Or on installation of the SDK?


Install the SDK
---------------

To install the SDK via pip, use the following command::

    pip install python-myra

Writing your first program
--------------------------

.. todo:: Save your `settings.conf` file in a known location. (Or, how to do this?)


The first thing you need is to initialize the Myra API client and connect to the remote server.::

    from os.path import expanduser, join
    from myra_client import clientv2

    CONF_FILE = join(expanduser('~'), '.myra', 'settings.conf')

    # Create configuration
    config = clientv2.get_config(CONF_FILE)

    # Connect API
    api = clientv2.connect(config)

A `client` instance should only be created once in the lifecycle of an application.

Next, we'll configure this client to utilize our demo intent and entity models. You'll find the IDs of the demo models in the dashboard, look for "demo_model" in Intent Models and "demo_model_entity" in Entity Models::

    # Set intent model
    api.set_intent_model("xxxx")

    # Set entity model
    api.set_entity_model("yyyy")

Now we're all set to start using the API. Let's start with a sample sentence to analyze::

    sentence = "what's a good coffee shop in San Francisco?"

    # Get results
    result = api.get(sentence)

    print("Intent: ", result.intent.label, result.intent.score)
    print("Entities: ", result.entities.entities)

Calling the `client.get()` method sends a request to Myra and returns an object of type `InferenceResult`, a Python class that represents the result of this API call.

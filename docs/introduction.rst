Introduction
===============

Welcome to Myra! Here's a quick guide on using the python-myra library.

Zero to bot in 3 steps

Giving a whole new meaning to quick start.


Step 1
---------------------

Go to api.myralabs.com and sign up for an account. Note your credentials.


Step 2
---------------------

Clone the git repo
Edit the config file with your credentials


Step 3
----------------------

Run python hello.py



A Minimal Application
---------------------

Now that you've got something running - lets explore how to dive deeper.

There are a few things,

- Create intent models
- Create entity models
-

A minimal Flask application looks something like this::

    from flask import Flask
    app = Flask(__name__)

    @app.route('/')
    def hello_world():
        return 'Hello, World!'

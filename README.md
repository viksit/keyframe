# Pyra
Python library to access Myra natural language APIs. 

Please retrieve your Account ID, Account Secret, and Intent Model ID or Entity ID from the Myra dashboard.

```sh
~/ $ git clone git@github.com:myralabs/python-myra.git
~/ $ cd python-myra/

~/python-myra $ export MYRA_ACCOUNT_ID=xxx
~/python-myra $ export MYRA_ACCOUNT_SECRET=xxx
~/python-myra $ export MYRA_INTENT_MODEL_ID=xxx
~/python-myra $ export MYRA_ENTITY_MODEL_ID=xxx

~/python-myra $ python myraclient/client.py "Hello"
intent: ('myra.intent.greeting.hello', 0.9736359715461731)

~/python-myra $ python myraclient/client.py "Goodbye"
intent: ('myra.intent.greeting.bye', 0.9181773662567139)
```

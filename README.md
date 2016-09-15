# python-myra
Clients for access to Myra apis
If you would like to try out getting better intents for your users messages, please do the following. We have a client library in python (open-sourced), and I have set up an account for you and built a model for intents.

------------
~/work $ git clone git@github.com:myralabs/python-myra.git

~/work $ cd python-myra/

~/work/python-myra $ 

~/work/python-myra $ export MYRA_ACCOUNT_ID=xxx

~/work/python-myra $ export MYRA_ACCOUNT_SECRET=xxx

~/work/python-myra $ export MYRA_INTENT_MODEL_ID=xxx

~/work/python-myra $ python myra/client.py "There is a backed up toilet in the ladies room on the 2nd floor of 8625 North side of building. It is the last stall on the left."

intent: (u'Plumbing', 0.9399809241294861)

~/work/python-myra $ 

~/work/python-myra $ python myra/client.py "please provide key SL057 for desk locks. Thanks"

intent: (u'Facilities', 0.9961974620819092)

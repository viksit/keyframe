```
from os.path import expanduser, join
from myra_client import clientv2

sentence = "whats a good coffee shop in the mission?"

# Set up configuration file path
CONF_FILE = join(expanduser('~'), '.myra', 'settings.conf')

# Create configuration
config = clientv2.get_config(CONF_FILE)

# Connect API
api = clientv2.connect(config)

# Set intent model ID
im = "xxxxyyy"
api.set_intent_model(im)

# Set entity model ID
em = "yyyxxxxx"
api.set_entity_model(em)

# Get results
result = api.get(sentence)

# Output
print("Intent: ", result.intent.label, result.intent.score)
print("Entities; ", result.entities.entity_dict)
```

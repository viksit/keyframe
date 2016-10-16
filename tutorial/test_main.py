from os.path import expanduser, join
from pymyra.api import client

sentence = "whats a good coffee shop in the mission?"

CONF_FILE = join(expanduser('~'), '.myra', 'settings.conf')

# Create configuration
config = client.get_config(CONF_FILE)

# Connect API
api = client.connect(config)

# Set intent model
im = config.get("model.intent1").get("model_id")
api.set_intent_model(im)

# Set entity model
em = config.get("model.entity1").get("model_id")
api.set_entity_model(em)

# Get results
result = api.get(sentence)

print("Intent: ", result.intent.label, result.intent.score)
print("Entities; ", result.entities.entity_dict)
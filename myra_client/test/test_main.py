from myra_client import clientv2

sentence = "whats a good coffee shop in the mission?"

# Create configuration
config = clientv2.get_config()

# Connect API
api = clientv2.connect(config)

# Set intent model
im = config.get("model.intent1").get("model_id")
api.set_intent_model(im)

# Set entity model
em = config.get("model.entity1").get("model_id")
api.set_entity_model(em)

# Get results
(intent, score), entities = api.get(sentence)

print("Intent/Score: ", intent, score)
print("Entities; ", entities)

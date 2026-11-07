"""Print the number of blocks in the Kāpiti district (pipeline/kapiti_blocks.json)."""
import json, os
print(len(json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "kapiti_blocks.json")))))

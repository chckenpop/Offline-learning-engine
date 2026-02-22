import json, requests

url = ""
key = ""
with open('c:/VS CODE/Techathon/Techathon00/Offline-learning-engine/backend/.env', 'r') as f:
    for line in f:
        if line.startswith('SUPABASE_URL='):
            url = line.strip().split('=', 1)[1].strip("'\"")
        elif line.startswith('SUPABASE_KEY='):
            key = line.strip().split('=', 1)[1].strip("'\"")

headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

output = {}

# Try delivery_concepts
for table in ['delivery_concepts', 'delivery_concept', 'concepts']:
    res = requests.get(f"{url}/rest/v1/{table}?limit=1", headers=headers)
    output[table] = {"status": res.status_code, "data": res.json() if res.ok else res.text}

# Check the specific concept ID from lesson debug
concept_id = "8f0300d7-0580-44cb-9553-f9af17c18cfc"
res = requests.get(f"{url}/rest/v1/delivery_concepts?id=eq.{concept_id}&limit=1", headers=headers)
output["specific_concept"] = {"status": res.status_code, "data": res.json() if res.ok else res.text}

with open('concept_debug.json', 'w') as f:
    json.dump(output, f, indent=2)
print("Done. Check concept_debug.json")

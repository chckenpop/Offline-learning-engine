import requests
import json

SUPABASE_URL = "https://njqlzvelsatdwzwynyek.supabase.co"
SUPABASE_KEY = "sb_publishable_NOFcz2mruM_oYS8NaKWlIg_lrXZqXEM"
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

def check_schema():
    # Try to select one row to see columns
    res = requests.get(f"{SUPABASE_URL}/rest/v1/delivery_lessons?limit=1", headers=HEADERS)
    if res.ok:
        print("Columns found in delivery_lessons:")
        print(list(res.json()[0].keys()))
    else:
        print(f"Error: {res.status_code}")
        print(res.text)

if __name__ == "__main__":
    check_schema()

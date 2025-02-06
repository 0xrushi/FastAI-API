import os
import json
import requests

API_NAMES = ["users", "cart"]
BASE_URL = "http://localhost:8080"
SAVE_DIR = "./src/openapi/openapi_specs"
os.makedirs(SAVE_DIR, exist_ok=True)


def fetch_and_save_openapi(api_name):
    """Fetch OpenAPI JSON from a FastAPI and save it to a file."""
    url = f"{BASE_URL}/{api_name}/openapi.json"
    save_path = os.path.join(SAVE_DIR, f"{api_name}.json")

    try:
        print(f"Fetching OpenAPI spec from: {url}...")
        response = requests.get(url)
        response.raise_for_status()

        with open(save_path, "w") as f:
            json.dump(response.json(), f, indent=4)
        
        print(f"\033[92mSaved: {save_path}\033[0m")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching {api_name}: {e}")

for api in API_NAMES:
    fetch_and_save_openapi(api)

print("\nAll OpenAPI specs have been fetched and saved successfully!")

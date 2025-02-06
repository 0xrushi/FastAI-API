import os
import json
import jsonref
import requests
from pprint import pp
from openai import OpenAI

# Add color formatting for terminal output
BLUE = "\033[94m"
GREEN = "\033[92m"
RESET = "\033[0m"
YELLOW = "\033[93m"

FASTAPI_BASE_URL = "http://localhost:8000"
SAVE_DIR = "./src/openapi"

SYSTEM_MESSAGE = """
You are a helpful assistant.
Respond to the following prompt by using function_call and then summarize actions.
Ask for clarification if a user request is ambiguous.
"""
MAX_CALLS = 5


client = OpenAI()
url = f"{FASTAPI_BASE_URL}/openapi.json"
save_path = os.path.join(SAVE_DIR, "openapi.json")

# save OpenAPI spec
try:
    print(f"Fetching OpenAPI spec from: {url}...")
    response = requests.get(url)
    response.raise_for_status()

    with open(save_path, "w") as f:
        json.dump(response.json(), f, indent=4)
    
    print(f"\033[92mSaved: {save_path}\033[0m")
except requests.exceptions.RequestException as e:
    print(f"Error fetching {FASTAPI_BASE_URL}: {e}")

# Load OpenAPI spec
with open('./src/openapi/single_openapi_specs.json', 'r') as f:
    openapi_spec = jsonref.loads(f.read())


def openapi_to_functions(openapi_spec):
    functions = []

    for path, methods in openapi_spec["paths"].items():
        for method, spec_with_ref in methods.items():
            spec = jsonref.replace_refs(spec_with_ref)

            function_name = spec.get("operationId")
            desc = spec.get("description") or spec.get("summary", "")

            schema = {"type": "object", "properties": {}}

            req_body = (
                spec.get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema")
            )
            if req_body:
                schema["properties"]["requestBody"] = req_body

            params = spec.get("parameters", [])
            if params:
                param_properties = {
                    param["name"]: param["schema"]
                    for param in params
                    if "schema" in param
                }
                schema["properties"]["parameters"] = {
                    "type": "object",
                    "properties": param_properties,
                }

            functions.append(
                {"type": "function", "function": {"name": function_name, "description": desc, "parameters": schema}}
            )

    return functions

def get_openai_response(functions, messages):
    return client.chat.completions.create(
        model="gpt-3.5-turbo-16k",
        tools=functions,
        tool_choice="auto",
        temperature=0,
        messages=messages,
    )

def call_api(function_name, params):
    """Executes an actual API call to the FastAPI server based on OpenAI function calls."""
    
    for path, methods in openapi_spec["paths"].items():
        for method, spec_with_ref in methods.items():
            spec = jsonref.replace_refs(spec_with_ref)
            if spec.get("operationId") == function_name:
                url = FASTAPI_BASE_URL + path  # Construct full URL

                if "parameters" in params:
                    url = url.format(**params["parameters"])  # Fill path params

                headers = {"Content-Type": "application/json"}
                data = params.get("requestBody", {})

                print(f"{GREEN}📌 API Endpoint: {url} [{method.upper()}]{RESET}")
                
                print(f"{GREEN}📌 Parameters:{RESET}")
                pp(params)
                
                proceed = input(f"{YELLOW}Do you want to proceed with this API call? (Y/n): {RESET}").strip().lower()
                if proceed not in ['y', 'yes', '']:
                    status = f"Skipping {function_name} API call"
                    print(status)
                    return {"status": status}

                try:
                    if method.lower() == "get":
                        response = requests.get(url, params=params.get("parameters", {}), headers=headers)
                    else:
                        response = requests.request(method.upper(), url, json=data, headers=headers)

                    if response.status_code >= 400:
                        print(f"API Error {response.status_code}: {response.text}")
                        return {"error": f"API request failed with status {response.status_code}"}

                    return response.json()

                except requests.exceptions.RequestException as e:
                    print(f"Request Error: {e}")
                    return {"error": "API request failed"}

    return {"error": "Function not found in OpenAPI spec"}

def process_user_instruction(functions, instruction):
    num_calls = 0
    messages = [
        {"content": SYSTEM_MESSAGE, "role": "system"},
        {"content": instruction, "role": "user"},
    ]

    while num_calls < MAX_CALLS:
        response = get_openai_response(functions, messages)
        message = response.choices[0].message

        if not message.tool_calls:
            print("\n>> Final Assistant Message:\n")
            print(message.content)
            break  # No more function calls

        messages.append(
            {
                "role": "assistant",
                "tool_calls": message.tool_calls,
            }
        )

        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            api_response = call_api(function_name, function_args)

            messages.append(
                {
                    "role": "tool",
                    "name": tool_call.function.name,  
                    "tool_call_id": tool_call.id,  
                    "content": json.dumps(api_response),  
                }
            )

        num_calls += 1

    if num_calls >= MAX_CALLS:
        print(f"Reached max chained function calls: {MAX_CALLS}")

def main():
    USER_INSTRUCTION = """
    Create a user and get userID, then add an item to cart for that userID.
    """
    functions = openapi_to_functions(openapi_spec)
    process_user_instruction(functions, USER_INSTRUCTION)

if __name__ == "__main__":
    main()
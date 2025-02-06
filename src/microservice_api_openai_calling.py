import os
import json
import jsonref
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
from pprint import pp
from openai import OpenAI
from rich.console import Console
from rich.prompt import Confirm

console = Console()

@dataclass
class APIConfig:
    """Configuration for API settings"""
    base_url: str = "http://localhost:8080"
    specs_dir: str = "./src/openapi/openapi_specs"
    max_calls: int = 5
    api_names: List[str] = None
    debug: bool = True
    api_log_file: str = "api_log.json"

    def __post_init__(self):
        if self.api_names is None:
            self.api_names = ["cart", "users"]

class APIOrchestrator:
    def __init__(self, config: APIConfig):
        self.config = config
        self.client = OpenAI()
        self.console = Console()
        self.openapi_specs = self._load_all_specs()
        self.functions = self._convert_specs_to_functions()
        
        if self.config.debug:
            self._debug_print_functions()
    
    def _debug_print_functions(self):
        """Print available functions for debugging"""
        console.rule("[yellow]Available API Functions")
        for func in self.functions:
            console.print(f"[green]Function:[/green] {func['function']['name']}")
            console.print(f"[blue]Description:[/blue] {func['function']['description']}")
            console.print(f"[cyan]Parameters:[/cyan]")
            pp(func['function']['parameters'])
            console.print()

    def _load_all_specs(self) -> Dict:
        """Load all OpenAPI specifications"""
        specs = {}
        for api in self.config.api_names:
            try:
                file_path = os.path.join(self.config.specs_dir, f"{api}.json")
                console.print(f"[yellow]Loading spec from: {file_path}")
                
                with open(file_path, "r") as f:
                    spec_content = f.read()
                    console.print(f"[cyan]Raw spec content length: {len(spec_content)} bytes")
                    specs[api] = jsonref.loads(spec_content)
                
                # Debug loaded paths
                if self.config.debug:
                    console.print(f"\n[yellow]Available paths in {api}:[/yellow]")
                    for path, methods in specs[api]["paths"].items():
                        console.print(f"[cyan]Path: {path}[/cyan]")
                        for method, details in methods.items():
                            console.print(f"  [green]{method.upper()}[/green]")
                            if "operationId" in details:
                                console.print(f"    OperationId: {details['operationId']}")
                
            except FileNotFoundError:
                console.print(f"[red]Error: Spec file not found: {file_path}")
            except json.JSONDecodeError as e:
                console.print(f"[red]Error: Invalid JSON in {file_path}: {str(e)}")
            except Exception as e:
                console.print(f"[red]Error loading {api} spec: {str(e)}")
        return specs
    
    def _convert_specs_to_functions(self) -> List[Dict]:
        """Convert OpenAPI specs to OpenAI function definitions"""
        functions = []
        
        for api_name, spec in self.openapi_specs.items():
            for path, methods in spec["paths"].items():
                for method, spec_with_ref in methods.items():
                    spec = jsonref.replace_refs(spec_with_ref)
                    
                    # Generate operationId if not present
                    function_name = spec.get("operationId")
                    if not function_name:
                        # Create a function name from path and method
                        path_parts = [p for p in path.split("/") if p and not p.startswith("{")]
                        function_name = f"{method}_{'_'.join(path_parts)}"
                        if self.config.debug:
                            console.log(f"[yellow]Generated function name for {method} {path}: {function_name}")
                    
                    function_def = {
                        "type": "function",
                        "function": {
                            "name": function_name,
                            "description": f"{spec.get('description') or spec.get('summary', '')} Method: {method.upper()}, Path: {path} (from {api_name} API)",
                            "parameters": self._build_parameters_schema(spec)
                        }
                    }
                    functions.append(function_def)
                    
        return functions
    def _build_parameters_schema(self, spec: Dict) -> Dict:
        """Build OpenAI function parameters schema from OpenAPI spec"""
        schema = {"type": "object", "properties": {}}
        
        # Handle request body
        req_body = (spec.get("requestBody", {})
                   .get("content", {})
                   .get("application/json", {})
                   .get("schema"))
        if req_body:
            schema["properties"]["requestBody"] = req_body
            
        # Handle parameters
        params = spec.get("parameters", [])
        if params:
            param_properties = {
                param["name"]: param["schema"]
                for param in params
                if "schema" in param
            }
            if param_properties:
                schema["properties"]["parameters"] = {
                    "type": "object",
                    "properties": param_properties
                }
            
        return schema

    def _get_full_path(self, base_path: str, api_name: str, endpoint_path: str) -> str:
        """Construct full API path by properly joining base path, API name, and endpoint path"""
        # Ensure base path does not end with a slash
        base_path = base_path.rstrip('/')
        # Ensure endpoint starts with a slash
        endpoint_path = '/' + endpoint_path.lstrip('/')
        # Prepend API name to ensure correct routing
        return f"{base_path}/{api_name}{endpoint_path}"
        
    def process_instruction(self, instruction: str) -> None:
        """Process user instruction and execute necessary API calls"""
        messages = [
            {
                "role": "system",
                "content": """You are a helpful assistant. Use the available API functions to accomplish the user's request.
                             First create a user using the users API endpoint, then use the returned user ID to add items to their cart.
                             The exact function names and parameters are shown in the function definitions - use these exactly as shown.
                             Ask for clarification if a user request is ambiguous."""
            },
            {"role": "user", "content": instruction}
        ]
        
        num_calls = 0
        while num_calls < self.config.max_calls:
            try:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo-16k",
                    tools=self.functions,
                    tool_choice="auto",
                    temperature=0,
                    messages=messages
                )
                
                message = response.choices[0].message
                
                if not message.tool_calls:
                    console.print("\nFinal Assistant Message:", style="bold green")
                    console.print(message.content)
                    break
                    
                messages.append({
                    "role": "assistant",
                    "tool_calls": message.tool_calls,
                })
                
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    api_response = self.execute_api_call(function_name, function_args)
                    
                    messages.append({
                        "role": "tool",
                        "name": tool_call.function.name,
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(api_response)
                    })
                    
                num_calls += 1
                
            except Exception as e:
                console.print(f"[red]Error processing instruction: {str(e)}")
                break
                
        if num_calls >= self.config.max_calls:
            console.print(f"[yellow]Reached maximum number of API calls: {self.config.max_calls}")


    def _log_api_call(self, method, url, params, request_body):
        """Log API call details to a JSON file for later replay"""
        log_entry = {
            "method": method.upper(),
            "url": url,
            "params": params,
            "request_body": request_body
        }

        log_file = self.config.api_log_file
        try:
            if os.path.exists(log_file):
                with open(log_file, "r") as f:
                    logs = json.load(f)
            else:
                logs = []

            logs.append(log_entry)

            with open(log_file, "w") as f:
                json.dump(logs, f, indent=4)

        except Exception as e:
            console.print(f"[red]Failed to log API call: {str(e)}")

    def execute_api_call(self, function_name: str, params: Dict) -> Dict:
        """Execute and log API call"""
        for api_name, spec in self.openapi_specs.items():
            for path, methods in spec["paths"].items():
                for method, details in methods.items():
                    current_func_name = details.get("operationId") or f"{method}_{path.replace('/', '_')}"

                    if current_func_name == function_name:
                        full_path = f"{self.config.base_url}/{api_name}{path}"

                        if "parameters" in params:
                            try:
                                full_path = full_path.format(**params["parameters"])
                                console.print(f"\n[yellow]API Request:[/yellow] {method.upper()} {full_path}")
                            except KeyError as e:
                                console.print(f"[red]Missing path parameter: {e}")
                                return {"error": f"Missing path parameter: {e}"}

                        if "parameters" not in params:
                            console.print(f"\n[yellow]API Request:[/yellow] {method.upper()} {full_path}")
                        if "requestBody" in params:
                            console.print(f"[yellow]Request Body:[/yellow] {json.dumps(params['requestBody'], indent=4)}")

                        confirm = Confirm.ask("[yellow]Proceed with API call?[/yellow]", default=True)
                        if not confirm:
                            console.print("[red]API call canceled by user.[/red]")
                            return {"error": "API call canceled by user"}

                        try:
                            response = requests.request(
                                method=method.upper(),
                                url=full_path,
                                json=params.get("requestBody"),
                                params=params.get("parameters") if method.lower() == "get" else None,
                                headers={"Content-Type": "application/json"}
                            )
                            response.raise_for_status()

                            self._log_api_call(method, full_path, params.get("parameters"), params.get("requestBody"))

                            return response.json()

                        except requests.exceptions.RequestException as e:
                            console.print(f"[red]API call failed: {str(e)}")
                            return {"error": f"API call failed: {str(e)}"}

        return {"error": f"Function '{function_name}' not found in OpenAPI specs"}

def main():
    config = APIConfig(debug=False)
    orchestrator = APIOrchestrator(config)
    instruction = "Create a user and get userID, then add an item to cart for that userID. Get me user details for that userid"
    console.print(f"[green]Instruction: {instruction}")
    orchestrator.process_instruction(instruction)

if __name__ == "__main__":
    main()
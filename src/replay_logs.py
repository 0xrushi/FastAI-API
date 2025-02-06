import json
from time import sleep
import requests
from rich.console import Console
from rich.table import Table

console = Console()

API_LOG_FILE = "api_log.json"

def load_api_log():
    """Load API call log from JSON file."""
    try:
        with open(API_LOG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        console.print(f"[red]Error: Log file '{API_LOG_FILE}' not found.[/red]")
        return []
    except json.JSONDecodeError as e:
        console.print(f"[red]Error parsing JSON in '{API_LOG_FILE}': {str(e)}[/red]")
        return []

def replay_api_calls():
    """Replay all logged API calls."""
    api_calls = load_api_log()
    
    if not api_calls:
        console.print("[yellow]No API calls to replay.[/yellow]")
        return

    console.print(f"[cyan]Replaying {len(api_calls)} API calls...[/cyan]")

    table = Table(title="API Call Results")
    table.add_column("Method", style="bold")
    table.add_column("URL", style="cyan")
    table.add_column("Status Code", style="green")
    table.add_column("Response", style="magenta")

    for api_call in api_calls:
        method = api_call.get("method", "GET")
        url = api_call.get("url", "")
        params = api_call.get("params", {})
        request_body = api_call.get("request_body", {})

        try:
            response = requests.request(
                method=method,
                url=url,
                params=params if method.upper() == "GET" else None,
                json=request_body if method.upper() in ["POST", "PUT", "PATCH"] else None,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            table.add_row(
                method.upper(),
                url,
                str(response.status_code),
                response.text[:100] + ("..." if len(response.text) > 100 else "")
            )
            sleep(0.5)

        except requests.exceptions.RequestException as e:
            table.add_row(method.upper(), url, "[red]ERROR[/red]", str(e))

    console.print(table)

if __name__ == "__main__":
    replay_api_calls()

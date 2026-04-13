from fastmcp import FastMCP

# 1. Initialize the FastMCP server
# The name "DoctorProvider" will appear in your orchestrator logs
mcp = FastMCP("DoctorProvider")

# 2. Define the tool
@mcp.tool()
async def list_doctors(city: str, state: str) -> str:
    """
    Search for cardiologists and heart specialists based on location.
    
    Args:
        city: The city name (e.g., 'austin')
        state: The 2-letter state abbreviation (e.g., 'tx')
    """
    # Normalizing inputs to match our mock database keys
    city_norm = city.lower().strip()
    state_norm = state.lower().strip()
    
    print(f"[*] MCP Tool Triggered: list_doctors for {city_norm}, {state_norm}")

    # Mock database for the DevSecOps lab demo
    mock_db = {
        ("austin", "tx"): [
            "Dr. Sarah Miller - Austin Heart & Vascular (Rating: 4.9/5)",
            "Dr. James Chen - Capital Cardiology (Rating: 4.8/5)",
            "Dr. Elena Rodriguez - Heart Hospital of Austin (Rating: 4.7/5)"
        ],
        ("denver", "co"): [
            "Dr. Michael Thompson - Rocky Mountain Cardiology (Rating: 4.9/5)",
            "Dr. Lisa Nguyen - Denver Heart Center (Rating: 4.8/5)"
        ]
    }

    doctors = mock_db.get((city_norm, state_norm))

    if doctors:
        results_list = "\n".join([f"- {doc}" for doc in doctors])
        return f"Found the following highly-rated cardiologists in {city.title()}, {state.upper()}:\n{results_list}"
    
    return f"I couldn't find any specific cardiologists in {city.title()}, {state.upper()} in our local database."

if __name__ == "__main__":
    # 3. Start the server using the SSE transport on the default port 8000
    # The orchestrator (concierge_agent.py) expects this endpoint
    mcp.run(transport="sse")

import warnings
import os
from dotenv import load_dotenv
# We keep this because it defines the data structure for the agent
from a2a.types import AgentCard 

def setup_env() -> None:
    """Loads .env file and cleans up terminal noise."""
    load_dotenv(override=True)
    
    # Check if key is loaded (Optional helper)
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ Warning: OPENAI_API_KEY not found in environment!")

    # Silence unnecessary warnings for a cleaner CLI experience
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)

def display_agent_card(agent_card: AgentCard) -> None:
    """Standard Python print version of the Agent Card."""
    print(f"\n{'='*20} AGENT CARD {'='*20}")
    print(f"Name:        {agent_card.name}")
    print(f"Description: {agent_card.description}")
    print(f"Version:     {agent_card.version}")
    print(f"URL:         {agent_card.url}")
    print("-" * 52)
    
    if agent_card.skills:
        print("SKILLS:")
        for skill in agent_card.skills:
            print(f" • {skill.name}: {skill.description}")
    print("="*52 + "\n")

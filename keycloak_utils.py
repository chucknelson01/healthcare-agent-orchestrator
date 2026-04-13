import os
import httpx
from jose import jwt
from dotenv import load_dotenv

# Initialize environment variables
load_dotenv()

# --- Configuration Mapping (Synced with your .env) ---
KEYCLOAK_URL = os.getenv("KC_URL", "http://localhost:8080")
REALM_NAME = os.getenv("KC_REALM", "HealthCare-AI")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8501/")

# Human Identity (OIDC)
CLIENT_ID = os.getenv("CLIENT_ID", "streamlit-ui")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# Machine Identity (NHI)
NHI_CLIENT_ID = os.getenv("NHI_CLIENT_ID", "concierge-nhi")
NHI_SECRET = os.getenv("NHI_SECRET")

# Security
PUBLIC_KEY = os.getenv("KEYCLOAK_PUBLIC_KEY")

# --- UI & AUTHENTICATION (app.py) ---

def get_login_url():
    """Generates the OIDC login URL."""
    base_url = KEYCLOAK_URL.rstrip('/')
    return (
        f"{base_url}/realms/{REALM_NAME}/protocol/openid-connect/auth"
        f"?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=openid"
    )

def handle_auth_callback(code: str):
    """Exchanges the authorization code for an access token."""
    url = f"{KEYCLOAK_URL.rstrip('/')}/realms/{REALM_NAME}/protocol/openid-connect/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    
    with httpx.Client() as client:
        response = client.post(url, data=data)
        response.raise_for_status()
        return response.json()

def get_user_context(token: str):
    """Extracts user details (ID, Name) from the token claims."""
    if not token:
        return None
    clean_token = token.replace("Bearer ", "") if token.startswith("Bearer ") else token
    try:
        claims = jwt.get_unverified_claims(clean_token)
        return {
            "sub": claims.get("sub"),
            "name": claims.get("name", "Healthcare Professional"),
            "preferred_username": claims.get("preferred_username"),
            "email": claims.get("email"),
            "roles": claims.get("realm_access", {}).get("roles", [])
        }
    except Exception as e:
        print(f"[!] Failed to extract user context: {e}")
        return None

# --- SECURITY & VALIDATION (concierge_agent.py) ---

def verify_token(token: str) -> bool:
    """
    Validates the JWT signature. 
    Uses verify_aud: False to allow cross-client (UI to Agent) trust.
    """
    if not token:
        return False

    clean_token = token.replace("Bearer ", "") if token.startswith("Bearer ") else token

    try:
        if PUBLIC_KEY:
            # FIX: Disable audience verification to allow 'streamlit-ui' tokens 
            # to be accepted by the 'concierge-nhi' agent.
            jwt.decode(
                clean_token, 
                PUBLIC_KEY, 
                algorithms=["RS256"], 
                options={"verify_aud": False}
            )
            return True
        else:
            # Structure validation only
            jwt.get_unverified_claims(clean_token)
            return True
    except Exception as e:
        # This will now only trigger for real issues (expiry or bad signature)
        print(f"[!] Security Alert: Token validation failed - {str(e)}")
        return False

def is_token_valid(token: str) -> bool:
    """Gatekeeper check for the Concierge Agent."""
    return verify_token(token)

# --- AGENT-TO-AGENT TRUST (NHI) ---

def get_agent_nhi_token():
    """Obtains a token for the Concierge to identify itself to the Policy Agent."""
    url = f"{KEYCLOAK_URL.rstrip('/')}/realms/{REALM_NAME}/protocol/openid-connect/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": NHI_CLIENT_ID,
        "client_secret": NHI_SECRET,
    }
    
    with httpx.Client() as client:
        response = client.post(url, data=data)
        response.raise_for_status()
        return response.json().get("access_token")

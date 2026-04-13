# 🏥 Healthcare Agent Orchestrator

A secure, multi-agent system designed for healthcare clinicians. This orchestrator coordinates between a **Policy Agent** and a **Provider Database (MCP)**, with identity validation enforced via **Keycloak (OIDC)** and local RSA signature verification.

---

## 📁 Project Structure

| File | Role | Description |
| :--- | :--- | :--- |
| **`concierge_agent.py`** | **Orchestrator** | The LangGraph brain and FastAPI entry point (Port 9996). |
| **`mcpserver.py`** | **Provider Tool** | MCP server providing doctor lookups via SSE (Port 8000). |
| **`policy_agent.py`** | **Policy Logic** | Core RAG implementation for insurance PDF searching (Port 9999). |
| **`a2a_policy_agent.py`**| **Policy Interface** | SDK wrapper for the Policy Agent connection. |
| **`app.py`** | **Frontend** | Streamlit UI for clinicians (Port 8501). |
| **`keycloak_utils.py`** | **Security** | Handles JWT decoding using the local Realm Public Key. |
| **`helpers.py`** | **Utilities** | Environment and configuration loader. |
| **`requirements.txt`** | **Dependencies** | Python package manifest. |

---

## 🔑 Keycloak & Identity Configuration

This project uses the **`HealthCare-AI`** realm. Follow these steps to align your Keycloak instance with the system requirements:

### 1. Run Keycloak (Docker)
```bash
docker run -p 8080:8080 -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:latest start-dev

### 2. Realm & Keys
Create a Realm named HealthCare-AI.

Go to Realm Settings -> Keys -> RS256 and click Public Key.

Copy this string. You will need to format it with \n characters for the KEYCLOAK_PUBLIC_KEY variable in your .env.

### 3. Client Configurations
Client 1: streamlit-ui (Human Identity)

Client ID: streamlit-ui

Client Authentication: On (Confidential)

Valid Redirect URIs: http://localhost:8501/

Secret: Copy from the Credentials tab to CLIENT_SECRET in .env.

Client 2: concierge-nhi (Machine Identity / NHI)

Client ID: concierge-nhi

Client Authentication: On

Service Accounts Enabled: On

Secret: Copy from the Credentials tab to NHI_SECRET in .env.

4. Test User Setup (alice@bogus.com)
Create a user with username alice and email alice@bogus.com.

Set a permanent password (e.g., password123) in the Credentials tab and turn off Temporary.

Use this user to log in via the Streamlit UI to test identity-driven orchestration.

## 🚀 Installation & Environment
Environment Setup:
Bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
Environment Variables:
Create a .env file in the root directory. Do not commit this file to Git.

Plaintext
# --- Keycloak Server Settings ---
KC_URL=http://localhost:8080
KC_REALM=HealthCare-AI
REDIRECT_URI=http://localhost:8501/

# --- Human Identity Client (OIDC: streamlit-ui) ---
CLIENT_ID=streamlit-ui
CLIENT_SECRET=your_ui_secret

# --- Machine Identity Client (NHI: concierge-nhi) ---
NHI_CLIENT_ID=concierge-nhi
NHI_SECRET=your_nhi_secret

# --- Security: Realm Public Key (Single line with \n) ---
KEYCLOAK_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\nYOUR_KEY_HERE\n-----END PUBLIC KEY-----"

# --- AI & Agent Configuration ---
OPENAI_API_KEY=sk-proj-...
POLICY_AGENT_PORT=9999
## 🛠️ Execution Sequence
Run these in separate terminals to maintain the agent mesh:

Terminal 1: MCP Provider Server
Bash
python mcpserver.py
Wait for: Uvicorn running on http://0.0.0.0:8000

Terminal 2: Policy Agent
Bash
python policy_agent.py
Wait for: Policy Agent active on Port 9999

Terminal 3: Concierge Orchestrator
Bash
python concierge_agent.py
Wait for: Application startup complete (Port 9996)

Terminal 4: Streamlit UI
Bash
streamlit run app.py
Open http://localhost:8501 and log in as Alice.

🔐 Security Architecture
Local JWT Validation: Verification is performed locally using the RSA Public Key, ensuring high performance and Zero Trust security without redundant network calls to Keycloak.

Identity Propagation: The user's unique human_id is extracted from the JWT sub claim and injected into the LangGraph state, ensuring all sub-agent actions are context-aware.

SSE Handshake: The MCP server requires a formal initialize handshake before executing any tools, preventing unauthenticated or uninitialized command execution

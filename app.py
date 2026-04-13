import streamlit as st
import httpx
import os
from keycloak_utils import (
    get_login_url,
    handle_auth_callback,
    get_user_context
)

# --- Configuration ---
CONCIERGE_URL = os.getenv("CONCIERGE_URL", "http://localhost:9996/query")

st.set_page_config(page_title="Healthcare Concierge", layout="wide")

def main():
    st.title("🏥 Healthcare Agentic Concierge")
    st.markdown("---")

    # 1. HANDLE OIDC CALLBACK
    # Check if we are returning from Keycloak with an auth code
    query_params = st.query_params
    if "code" in query_params:
        auth_code = query_params.get("code")
        try:
            # Exchange code for tokens
            token_data = handle_auth_callback(auth_code)
            st.session_state.token = token_data.get("access_token")
            
            # Clear URL parameters and refresh
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Authentication Failed: {e}")

    # 2. MANAGE SESSION STATE
    if "token" not in st.session_state:
        st.info("Please log in to access the Clinical Assistant.")
        if st.button("Login with Keycloak"):
            login_url = get_login_url()
            st.markdown(f'<a href="{login_url}" target="_self">Click here to Login</a>', unsafe_allow_html=True)
        return

    # 3. EXTRACT USER CONTEXT
    user = get_user_context(st.session_state.token)
    if not user:
        st.warning("Session expired. Please log in again.")
        if st.button("Re-authenticate"):
            del st.session_state.token
            st.rerun()
        return

    st.sidebar.success(f"Logged in as: {user['name']}")
    st.sidebar.info(f"Role: {', '.join(user['roles']) if user['roles'] else 'Clinician'}")

    if st.sidebar.button("Logout"):
        del st.session_state.token
        st.rerun()

    # 4. CHAT INTERFACE
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask about patient policy or find local specialists..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Orchestrating Agents..."):
                try:
                    # Pass the Identity Token and the User Subject ID to the Concierge
                    headers = {
                        "Authorization": f"Bearer {st.session_state.token}",
                        "x-human-sub": user["sub"],
                        "Content-Type": "application/json"
                    }
                    
                    response = httpx.post(
                        CONCIERGE_URL,
                        json={"text": prompt},
                        headers=headers,
                        timeout=120.0
                    )
                    
                    if response.status_code == 200:
                        answer = response.json().get("agent_response", "No response from agent.")
                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                    elif response.status_code == 401:
                        st.error("🚨 Agent Authority Revoked: The Kill Switch is active in Keycloak.")
                    else:
                        st.error(f"Error from Concierge: {response.status_code} - {response.text}")
                
                except Exception as e:
                    st.error(f"System Error: {str(e)}")

if __name__ == "__main__":
    main()

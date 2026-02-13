import streamlit as st
import requests

# --- Configuration ---
API_URL = "http://localhost:8000/ask"

st.set_page_config(page_title="UET KAG System", page_icon="🎓")
st.title("🎓 UET Lahore Assistant")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle Input
if prompt := st.chat_input("Ask about UET departments..."):
    # User message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Bot response
    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("🧠 *Consulting the knowledge base...*")
        
        try:
            response = requests.post(API_URL, json={"question": prompt})
            
            if response.status_code == 200:
                data = response.json()
                answer_text = data.get("answer", "No answer provided.")
                cypher_code = data.get("generated_cypher", "")

                # Display the professional answer
                placeholder.markdown(answer_text)
                
                # Optional: Show the technical reasoning in a dropdown
                with st.expander("View Search Logic"):
                    st.code(cypher_code, language="cypher")

                st.session_state.messages.append({"role": "assistant", "content": answer_text})
            else:
                placeholder.error("System Error: Could not retrieve answer.")
                
        except Exception as e:
            placeholder.error(f"Connection Error: {e}")
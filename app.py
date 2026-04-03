import streamlit as st
import pdfplumber
import requests
import re

# ==============================
# CONFIG
# ==============================
N8N_WEBHOOK_URL = st.secrets["N8N_WEBHOOK_URL"]

st.set_page_config(page_title="AI Document Orchestrator", layout="centered")
st.title("AI Document Orchestrator (REST)")

# ==============================
# INPUTS
# ==============================
uploaded_file = st.file_uploader("Upload a document", type=["pdf", "txt"])
question = st.text_input("Ask what you want to extract (e.g. skills, summary, experience)")
email = st.text_input("Enter your email for report *")

# ==============================
# EMAIL VALIDATION
# ==============================
def is_valid_email(email):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email)

if email and not is_valid_email(email):
    st.warning("⚠️ Please enter a valid email address")

# ==============================
# TEXT EXTRACTION
# ==============================
def extract_text(file):
    if file.type == "application/pdf":
        with pdfplumber.open(file) as pdf:
            return "".join(page.extract_text() or "" for page in pdf.pages)
    else:
        return file.read().decode("utf-8", errors="ignore")

# ==============================
# MAIN BUTTON
# ==============================
if st.button("Extract Information"):

    if not uploaded_file or not question.strip():
        st.error("Please upload a document and enter a question.")
        st.stop()

    if not email or not is_valid_email(email):
        st.error("Please enter a valid email.")
        st.stop()

    text = extract_text(uploaded_file)

    # 🔥 LIMIT TEXT SIZE (VERY IMPORTANT)
    text = text[:5000]

    payload = {
        "question": question,
        "document_text": text,
        "recipient_email": email
    }

    try:
        with st.spinner("Sending to AI workflow..."):

            response = requests.post(
                N8N_WEBHOOK_URL,
                json=payload,
                timeout=30
            )

        if response.status_code == 200:
            res_json = response.json()

            st.success("✅ Request processed successfully")

            st.subheader("Final Answer")
            st.write(res_json.get("final_answer", "No answer returned"))

        else:
            st.error(f"Webhook failed: {response.status_code}")
            st.write(response.text)

    except Exception as e:
        st.error(f"Error: {e}")

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
# SESSION STATE
# ==============================
if "document_text" not in st.session_state:
    st.session_state.document_text = None

if "response_data" not in st.session_state:
    st.session_state.response_data = None

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
# EXTRACT BUTTON (ONLY TEXT NOW)
# ==============================
if st.button("Extract Information"):

    if not uploaded_file or not question.strip():
        st.error("Please upload a document and enter a question.")
        st.stop()

    with st.spinner("Extracting document text..."):
        text = extract_text(uploaded_file)

    st.session_state.document_text = text

    st.success("✅ Document processed successfully!")
    st.info("Now click 'Send Alert Mail' to generate AI response via n8n.")

# ==============================
# SEND TO N8N (MAIN LOGIC)
# ==============================
send_clicked = st.button(
    "Send Alert Mail",
    disabled=(
        not st.session_state.document_text or
        not email or
        not is_valid_email(email)
    )
)

if send_clicked:

    if not st.session_state.document_text:
        st.error("Please extract data first.")
        st.stop()

    if not email:
        st.error("❌ Email is required.")
        st.stop()

    if not is_valid_email(email):
        st.error("❌ Please enter a valid email address.")
        st.stop()

    payload = {
        "question": question,
        "document_text": st.session_state.document_text,  # 🔥 FIXED
        "recipient_email": email
    }

    try:
        with st.spinner("Sending to AI workflow (n8n)..."):
            response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=60)

        if response.status_code == 200:
            st.success("✅ Report generated and sent successfully!")

            try:
                res_json = response.json()
                st.session_state.response_data = res_json

                st.subheader("AI Response")
                st.json(res_json)

            except:
                st.write(response.text)

        else:
            st.error(f"Webhook failed: {response.status_code}")
            st.write(response.text)

    except Exception as e:
        st.error(f"Error sending to n8n: {e}")

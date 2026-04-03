import streamlit as st
import pdfplumber
import requests
import json
import re

# ==============================
# CONFIG
# ==============================
API_KEY = st.secrets["GEMINI_API_KEY"]
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
if "parsed_data" not in st.session_state:
    st.session_state.parsed_data = None

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
# CLEAN JSON FUNCTION
# ==============================
def clean_json(text):
    try:
        text = text.replace("```json", "").replace("```", "").strip()

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group()

        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*]", "]", text)

        return text.strip()
    except:
        return text

# ==============================
# EXTRACT BUTTON
# ==============================
if st.button("Extract Information"):

    if not uploaded_file or not question.strip():
        st.error("Please upload a document and enter a question.")
        st.stop()

    text = extract_text(uploaded_file)

    # 🔥 DYNAMIC PROMPT
    prompt = f"""
You are an intelligent document analysis assistant.

TASK:
Extract information from the document based on the user's question.

USER QUESTION:
{question}

DOCUMENT:
{text}

RULES:
- Return ONLY valid JSON
- No explanation
- No markdown
- No backticks
- Use structured format
- Keep output concise and relevant

OUTPUT FORMAT:
{{
  "question": "{question}",
  "answer": "...",
  "data": {{}}
}}
"""

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY
    }

    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        with st.spinner("Processing document..."):
            resp = requests.post(url, headers=headers, json=body, timeout=30)
            resp.raise_for_status()
            res_json = resp.json()

        output = res_json["candidates"][0]["content"]["parts"][0]["text"]
        clean_output = clean_json(output)

        try:
            parsed = json.loads(clean_output)
            st.session_state.parsed_data = parsed

            st.subheader("AI Extracted Output")
            st.json(parsed)

            # 🔥 SMART DISPLAY
            if "data" in parsed:
                data = parsed["data"]

                st.markdown("### Extracted Information")

                for key, value in data.items():
                    st.markdown(f"#### {key.capitalize()}")

                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                st.write(item)
                            else:
                                st.write(f"- {item}")
                    else:
                        st.write(value)

        except json.JSONDecodeError:
            st.error("Response was not valid JSON")
            st.code(output)

    except Exception as e:
        st.error(f"Request error: {e}")

# ==============================
# SEND TO N8N
# ==============================
send_clicked = st.button(
    "Send Alert Mail",
    disabled=(
        not st.session_state.parsed_data or
        not email or
        not is_valid_email(email)
    )
)

if send_clicked:

    if not st.session_state.parsed_data:
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
        "extracted_json": st.session_state.parsed_data,
        "recipient_email": email
    }

    try:
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=30)

        if response.status_code == 200:
            st.success("✅ Report generated and sent successfully to your email.")

            with st.expander("View technical response"):
                st.code(response.text)

        else:
            st.error(f"Webhook failed: {response.status_code}")
            st.write(response.text)

    except Exception as e:
        st.error(f"Error sending to n8n: {e}")

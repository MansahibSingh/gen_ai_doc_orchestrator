import streamlit as st
import pdfplumber
import requests
import json
import re
import time

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

if "last_call_time" not in st.session_state:
    st.session_state.last_call_time = 0

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
# GEMINI CALL WITH RETRY + FIXED MODEL
# ==============================
def call_gemini(prompt):

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY
    }

    body = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }

    for attempt in range(3):
        try:
            time.sleep(2)  # prevent rate limit

            response = requests.post(url, headers=headers, json=body, timeout=30)

            if response.status_code == 429:
                st.warning("⏳ Rate limit hit... retrying")
                time.sleep(5)
                continue

            if response.status_code == 404:
                st.error("❌ Model not found. Check API key or model name.")
                return None

            response.raise_for_status()
            return response.json()

        except Exception as e:
            if attempt == 2:
                raise e
            time.sleep(3)

# ==============================
# EXTRACT BUTTON
# ==============================
if st.button("Extract Information"):

    # Prevent rapid clicks
    if time.time() - st.session_state.last_call_time < 3:
        st.warning("⏳ Please wait before making another request")
        st.stop()

    st.session_state.last_call_time = time.time()

    if not uploaded_file or not question.strip():
        st.error("Please upload a document and enter a question.")
        st.stop()

    text = extract_text(uploaded_file)

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
- Keep output concise

OUTPUT FORMAT:
{{
  "question": "{question}",
  "answer": "...",
  "data": {{}}
}}
"""

    try:
        with st.spinner("Processing document..."):
            res_json = call_gemini(prompt)

        if res_json is None:
            st.stop()

        output = res_json["candidates"][0]["content"]["parts"][0]["text"]
        clean_output = clean_json(output)

        parsed = json.loads(clean_output)
        st.session_state.parsed_data = parsed

        st.subheader("AI Extracted Output")
        st.json(parsed)

    except json.JSONDecodeError:
        st.error("Invalid JSON from model")
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

    payload = {
        "question": question,
        "extracted_json": st.session_state.parsed_data,
        "recipient_email": email
    }

    try:
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=30)

        if response.status_code == 200:
            st.success("✅ Report generated and sent successfully to your email.")

        else:
            st.error(f"Webhook failed: {response.status_code}")
            st.write(response.text)

    except Exception as e:
        st.error(f"Error sending to n8n: {e}")

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

# Primary model first, then fallback if your key/project cannot access the first one
PRIMARY_MODEL = st.secrets.get("GEMINI_MODEL", "gemini-2.5-flash")
MODEL_CANDIDATES = list(dict.fromkeys([PRIMARY_MODEL, "gemini-1.5-flash-002"]))

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
def is_valid_email(email: str) -> bool:
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None

if email and not is_valid_email(email):
    st.warning("⚠️ Please enter a valid email address")

# ==============================
# TEXT EXTRACTION
# ==============================
def extract_text(file) -> str:
    if file.type == "application/pdf":
        with pdfplumber.open(file) as pdf:
            return "".join(page.extract_text() or "" for page in pdf.pages)
    return file.read().decode("utf-8", errors="ignore")

# ==============================
# CLEAN JSON FUNCTION
# ==============================
def clean_json(text: str) -> str:
    try:
        text = text.replace("```json", "").replace("```", "").strip()

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group()

        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*]", "]", text)

        return text.strip()
    except Exception:
        return text

# ==============================
# GEMINI CALL WITH RETRY + FALLBACK
# ==============================
def call_gemini(prompt: str):
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY,
    }

    body = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        # JSON mode helps reduce malformed responses
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    last_error = None

    for model in MODEL_CANDIDATES:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

        for attempt in range(3):
            try:
                time.sleep(2)  # light throttle to reduce 429s
                response = requests.post(url, headers=headers, json=body, timeout=30)

                if response.status_code == 404:
                    last_error = f"Model not found: {model}"
                    break  # try next model

                if response.status_code == 429:
                    last_error = f"Rate limit hit for model: {model}"
                    time.sleep(5)
                    continue

                response.raise_for_status()
                return response.json(), model

            except requests.RequestException as e:
                last_error = str(e)
                if attempt == 2:
                    break
                time.sleep(3)

    raise RuntimeError(last_error or "Gemini request failed")

# ==============================
# EXTRACT BUTTON
# ==============================
if st.button("Extract Information"):

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
            res_json, used_model = call_gemini(prompt)

        output = res_json["candidates"][0]["content"]["parts"][0]["text"]
        clean_output = clean_json(output)

        parsed = json.loads(clean_output)
        st.session_state.parsed_data = parsed

        st.subheader("AI Extracted Output")
        st.caption(f"Model used: {used_model}")
        st.json(parsed)

        if "data" in parsed and isinstance(parsed["data"], dict):
            st.markdown("### Extracted Information")
            for key, value in parsed["data"].items():
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

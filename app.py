import streamlit as st
import pdfplumber
import requests
import json
import re

# ==============================
# CONFIG
# ==============================
API_KEY = st.secrets["GEMINI_API_KEY"]

st.set_page_config(page_title="AI Document Orchestrator", layout="centered")
st.title("AI Document Orchestrator (REST)")

uploaded_file = st.file_uploader("Upload a document", type=["pdf", "txt"])
question = st.text_input("Ask a question about the document")


# ==============================
# TEXT EXTRACTION
# ==============================
def extract_text(file):
    if file.type == "application/pdf":
        with pdfplumber.open(file) as pdf:
            text = "".join(page.extract_text() or "" for page in pdf.pages)
        return text
    else:
        return file.read().decode("utf-8")


# ==============================
# CLEAN JSON FUNCTION (IMPORTANT)
# ==============================
def clean_json(text):
    try:
        # Extract JSON block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return text

        json_text = match.group()

        # Remove trailing commas
        json_text = re.sub(r",\s*}", "}", json_text)
        json_text = re.sub(r",\s*]", "]", json_text)

        # Remove unwanted markdown if present
        json_text = json_text.replace("```json", "").replace("```", "")

        return json_text.strip()

    except Exception:
        return text


# ==============================
# MAIN BUTTON
# ==============================
if st.button("Extract Information"):

    if not uploaded_file or not question:
        st.error("Please upload a document and enter a question.")
        st.stop()

    # Extract text
    text = extract_text(uploaded_file)

    # ==============================
    # PROMPT (STRICT JSON)
    # ==============================
    prompt = f"""
You are a strict JSON generator.

TASK:
Extract ONLY the key skills from the document based on the question.

RULES:
- Output ONLY JSON
- No explanation
- No markdown
- No backticks
- No text before or after JSON
- Use double quotes
- No trailing commas

FORMAT:
{{
  "key_skills": ["skill1", "skill2", "skill3"]
}}

Document:
{text}

Question:
{question}
"""

    # ==============================
    # GEMINI API CALL (FIXED MODEL)
    # ==============================
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
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        resp.raise_for_status()
        res_json = resp.json()

        st.subheader("AI Extracted Output")

        # Extract model output
        output = res_json["candidates"][0]["content"]["parts"][0]["text"]

        # ==============================
        # CLEAN + PARSE JSON
        # ==============================
        clean_output = clean_json(output)

        try:
            parsed = json.loads(clean_output)
            st.json(parsed)

        except json.JSONDecodeError:
            st.error("Response was not valid JSON")
            st.code(output)

    except requests.HTTPError as http_err:
        st.error(f"HTTP error: {http_err}")

    except Exception as e:
        st.error(f"Request error: {e}")

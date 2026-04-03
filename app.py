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

        # Remove trailing commas
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*]", "]", text)

        return text.strip()
    except Exception:
        return text


# ==============================
# MAIN BUTTON
# ==============================
if st.button("Extract Information"):

    if not uploaded_file or not question.strip():
        st.error("Please upload a document and enter a question.")
        st.stop()

    text = extract_text(uploaded_file)

    prompt = f"""
You are a strict JSON generator.

TASK:
Extract ONLY the key skills from the document based on the question.

RULES:
- Output ONLY valid JSON
- No explanation
- No markdown
- No backticks
- No text before or after JSON
- Use double quotes
- No numbering
- No trailing commas
- Return only one JSON object

FORMAT:
{{
  "key_skills": ["skill1", "skill2", "skill3"]
}}

Document:
{text}

Question:
{question}
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
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        resp.raise_for_status()
        res_json = resp.json()

        st.subheader("AI Extracted Output")

        output = res_json["candidates"][0]["content"]["parts"][0]["text"]
        clean_output = clean_json(output)

        try:
            parsed = json.loads(clean_output)

            # Cleaner display for your screenshot style
            st.json(parsed)

            # Optional: show skills without Streamlit list indices
            st.markdown("### Key Skills")
            for skill in parsed.get("key_skills", []):
                st.write(f"- {skill}")

        except json.JSONDecodeError:
            st.error("Response was not valid JSON")
            st.code(output)

    except requests.HTTPError as http_err:
        st.error(f"HTTP error: {http_err}")

    except Exception as e:
        st.error(f"Request error: {e}")

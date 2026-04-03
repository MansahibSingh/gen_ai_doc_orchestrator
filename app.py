import streamlit as st
import pdfplumber
import requests
import json
import re

API_KEY = st.secrets["GEMINI_API_KEY"]

st.title("AI Document Orchestrator (REST)")

uploaded_file = st.file_uploader("Upload a document", type=["pdf", "txt"])
question = st.text_input("Ask a question about the document")


def extract_text(file):
    if file.type == "application/pdf":
        with pdfplumber.open(file) as pdf:
            text = "".join(page.extract_text() or "" for page in pdf.pages)
        return text
    else:
        return file.read().decode("utf-8")


def extract_json_from_text(text):
    """
    Extract ONLY JSON from model response
    """
    try:
        # Find JSON block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return match.group()
        return text
    except:
        return text


if st.button("Extract Information"):
    if uploaded_file and question:
        text = extract_text(uploaded_file)

        prompt = f"""
You are a JSON generator.

STRICT RULES:
- Output ONLY valid JSON
- No explanation
- No markdown
- No backticks
- No text before or after JSON
- Ensure valid syntax (double quotes, no trailing commas)

TASK:
Extract structured information from the document based on the question.

Document:
{text}

Question:
{question}

Return JSON like:
{{
  "answer": "...",
  "key_points": ["...", "..."]
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
            resp = requests.post(url, headers=headers, json=body, timeout=30)
            resp.raise_for_status()
            res_json = resp.json()

            st.subheader("AI Extracted Output")

            output = res_json["candidates"][0]["content"]["parts"][0]["text"]

            # ✅ STEP 1: Extract JSON safely
            clean_output = extract_json_from_text(output)

            # ✅ STEP 2: Remove garbage if exists
            clean_output = clean_output.strip()

            try:
                parsed = json.loads(clean_output)
                st.json(parsed)
            except json.JSONDecodeError:
                st.error("Still not valid JSON. Showing raw output:")
                st.code(output)

        except requests.HTTPError as http_err:
            st.error(f"HTTP error: {http_err}")
        except Exception as e:
            st.error(f"Request error: {e}")

    else:
        st.error("Please upload a document and enter a question.")

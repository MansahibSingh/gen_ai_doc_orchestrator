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

if st.button("Extract Information"):
    if uploaded_file and question:
        text = extract_text(uploaded_file)

        prompt = f"""
        Extract relevant information from the document based on the question.

        Document:
        {text}

        Question:
        {question}

        Return ONLY valid JSON.
        Do not include markdown, backticks, or explanation.
        """

        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"

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

            # ✅ CLEAN JSON (IMPORTANT FIX)
            clean_output = re.sub(r"```json|```", "", output).strip()

            try:
                parsed = json.loads(clean_output)
                st.json(parsed)
            except json.JSONDecodeError:
                st.warning("Response was not perfectly formatted JSON. Showing raw output:")
                st.write(output)

        except requests.HTTPError as http_err:
            st.error(f"HTTP error: {http_err}")
        except Exception as e:
            st.error(f"Request error: {e}")

    else:
        st.error("Please upload a document and enter a question.")

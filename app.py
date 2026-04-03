import streamlit as st
import pdfplumber
import requests
import json

API_KEY = st.secrets["GEMINI_API_KEY"]

st.title("AI Document Orchestrator")

uploaded_file = st.file_uploader("Upload a document", type=["pdf", "txt"])
question = st.text_input("Ask a question about the document")

# Extract text
def extract_text(file):
    if file.type == "application/pdf":
        with pdfplumber.open(file) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text
    else:
        return file.read().decode("utf-8")

# Gemini API call (direct HTTP)
def call_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"

    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.text}

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
        """

        result = call_gemini(prompt)

        st.subheader("AI Extracted Output")

        try:
            output = result["candidates"][0]["content"]["parts"][0]["text"]

            try:
                parsed = json.loads(output)
                st.json(parsed)
            except:
                st.write(output)

        except:
            st.error(result)

    else:
        st.error("Please upload a file and enter a question")

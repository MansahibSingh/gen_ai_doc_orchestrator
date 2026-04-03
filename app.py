import streamlit as st
import pdfplumber
import google.generativeai as genai
import json

# Configure API key
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

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

if st.button("Extract Information"):
    if uploaded_file and question:
        text = extract_text(uploaded_file)

        # ✅ Stable working model
        model = genai.GenerativeModel("gemini-pro")

        prompt = f"""
        You are an AI data extractor.

        Given the document:
        {text}

        And the question:
        {question}

        Extract only relevant information.

        Return STRICTLY valid JSON.
        No explanation.

        Example:
        {{
            "key": "value"
        }}
        """

        try:
            response = model.generate_content(prompt)
            output = response.text

            st.subheader("AI Extracted Output")

            # Try parsing JSON
            try:
                parsed = json.loads(output)
                st.json(parsed)
            except:
                st.write(output)

        except Exception as e:
            st.error(f"Error: {e}")

    else:
        st.error("Please upload a file and enter a question")

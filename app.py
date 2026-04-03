import streamlit as st
import pdfplumber
import google.generativeai as genai

# Load API key
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

st.title("AI Document Orchestrator")

uploaded_file = st.file_uploader("Upload a document", type=["pdf", "txt"])
question = st.text_input("Ask a question about the document")

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

        model = genai.GenerativeModel("gemini-pro")

        prompt = f"""
        You are an AI data extractor.

        Given the document:
        {text}

        And the user question:
        {question}

        Extract the most relevant information and return in JSON format.
        """

        response = model.generate_content(prompt)

        st.subheader("AI Extracted Output")
        st.write(response.text)

    else:
        st.error("Please upload a file and enter a question")

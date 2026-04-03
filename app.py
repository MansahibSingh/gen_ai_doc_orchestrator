import streamlit as st
import pdfplumber
import json
from google import genai

# Configure Google GenAI client with API key from secrets
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

st.title("AI Document Orchestrator (SDK)")
uploaded_file = st.file_uploader("Upload a document", type=["pdf", "txt"])
question = st.text_input("Ask a question about the document")

def extract_text(file):
    if file.type == "application/pdf":
        text = ""
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text
    else:
        return file.read().decode("utf-8")

if st.button("Extract Information"):
    if uploaded_file and question:
        text = extract_text(uploaded_file)
        prompt = f"Extract relevant information from the document below based on the question.\n\nDocument:\n{text}\n\nQuestion:\n{question}\n\nReturn only valid JSON."
        
        try:
            # Use the alias for latest Flash model to avoid deprecated versions
            response = client.models.generate_content(
                model="gemini-flash-latest",   # auto-updating alias
                contents=prompt
            )
            raw_output = response.text
            st.subheader("AI Extracted Output")
            try:
                data = json.loads(raw_output)
                st.json(data)   # nicely format JSON
            except json.JSONDecodeError:
                st.error("Response was not valid JSON:\n" + raw_output)
        except Exception as e:
            st.error(f"API Error: {e}")
    else:
        st.error("Please upload a document and enter a question.")

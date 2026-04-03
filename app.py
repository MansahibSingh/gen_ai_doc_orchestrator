import streamlit as st
import pdfplumber
import google.generativeai as genai
import json

# Configure API key
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

st.title("AI Document Orchestrator")

uploaded_file = st.file_uploader("Upload a document", type=["pdf", "txt"])
question = st.text_input("Ask a question about the document")

# Function to extract text
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

        # ✅ Use correct model
        model = genai.GenerativeModel("gemini-1.5-flash")

        # ✅ Better prompt for structured JSON
        prompt = f"""
        You are an AI data extractor.

        Given the document below:
        {text}

        And the user question:
        {question}

        Extract only the most relevant information.

        Return STRICTLY in valid JSON format.
        Do not add explanation.

        Example format:
        {{
            "field_1": "value",
            "field_2": "value"
        }}
        """

        try:
            response = model.generate_content(prompt)
            output = response.text

            st.subheader("AI Extracted Output")

            # Try to parse JSON
            try:
                parsed_json = json.loads(output)
                st.json(parsed_json)  # nice formatted view
            except:
                st.write(output)  # fallback if not proper JSON

        except Exception as e:
            st.error(f"Error: {e}")

    else:
        st.error("Please upload a file and enter a question")

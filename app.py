import streamlit as st
import pdfplumber
import google.generativeai as genai
import json

# Configure API key
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

        # ✅ Correct model (NO "models/" prefix)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
        Extract relevant information from the document based on the question.

        Document:
        {text}

        Question:
        {question}

        Return ONLY valid JSON.
        No explanation.
        """

        try:
            response = model.generate_content(prompt)

            # ✅ safer way to extract text
            output = response.candidates[0].content.parts[0].text

            st.subheader("AI Extracted Output")

            try:
                parsed = json.loads(output)
                st.json(parsed)
            except:
                st.write(output)

        except Exception as e:
            st.error(f"Error: {e}")

    else:
        st.error("Please upload a file and enter a question")

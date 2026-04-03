import streamlit as st
import pdfplumber

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

        st.subheader("Extracted Text (Preview)")
        st.write(text[:1000])  # show first 1000 chars

        st.success("Text extracted successfully!")
    else:
        st.error("Please upload a file and enter a question")

import json
import re
from typing import Any, Dict, Optional

import pdfplumber
import requests
import streamlit as st
from google import genai


# -----------------------------
# Page config
# -----------------------------
st.set_page_config(page_title="AI Document Orchestrator", layout="centered")
st.title("AI Document Orchestrator (REST)")

# -----------------------------
# Secrets
# -----------------------------
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
N8N_WEBHOOK_URL = st.secrets.get("N8N_WEBHOOK_URL", "")

if not GEMINI_API_KEY:
    st.error("Missing GEMINI_API_KEY in .streamlit/secrets.toml")
    st.stop()

# Use a valid Gemini model ID from Google's docs.
# You can change this to another available model in your account if needed.
MODEL_NAME = "gemini-2.5-flash"

client = genai.Client(api_key=GEMINI_API_KEY)


# -----------------------------
# Helpers
# -----------------------------
def extract_text(file) -> str:
    """Extract text from PDF or TXT upload."""
    if file is None:
        return ""

    file_type = (file.type or "").lower()

    if file_type == "application/pdf":
        try:
            file.seek(0)
            with pdfplumber.open(file) as pdf:
                pages_text = []
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    pages_text.append(page_text)
            return "\n".join(pages_text).strip()
        except Exception as e:
            raise RuntimeError(f"PDF text extraction failed: {e}")

    # TXT or other text-like file
    try:
        file.seek(0)
        raw = file.read()
        if isinstance(raw, bytes):
            return raw.decode("utf-8", errors="ignore").strip()
        return str(raw).strip()
    except Exception as e:
        raise RuntimeError(f"Text file extraction failed: {e}")


def call_gemini_for_json(document_text: str, question: str) -> Dict[str, Any]:
    """
    Ask Gemini to return structured JSON.
    Using structured outputs reduces malformed JSON issues.
    """
    prompt = f"""
You are a document analysis assistant.

Task:
Extract the 5 to 8 most relevant key-value pairs from the document that help answer the user's question.

Rules:
- Focus only on information relevant to the question.
- Return concise but useful values.
- Include a short final answer.
- Do not add markdown.
- Do not add explanations outside the JSON.
- Return only valid JSON that matches the provided schema.

User question:
{question}

Document text:
{document_text}
""".strip()

    schema = {
        "type": "object",
        "properties": {
            "question": {"type": "string"},
            "final_answer": {"type": "string"},
            "key_value_pairs": {
                "type": "array",
                "minItems": 5,
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"},
                        "value": {"type": "string"},
                        "evidence": {"type": "string"},
                    },
                    "required": ["key", "value", "evidence"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["question", "final_answer", "key_value_pairs"],
        "additionalProperties": False,
    }

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": schema,
        },
    )

    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned an empty response.")

    # Since structured output should already be JSON, parse directly.
    return json.loads(text)


def send_to_n8n(
    webhook_url: str,
    document_text: str,
    question: str,
    extracted_json: Dict[str, Any],
    recipient_email: str,
) -> Dict[str, Any]:
    payload = {
        "question": question,
        "document_text": document_text,
        "extracted_json": extracted_json,
        "recipient_email": recipient_email,
    }

    resp = requests.post(webhook_url, json=payload, timeout=60)
    resp.raise_for_status()

    try:
        return resp.json()
    except Exception:
        return {"raw_response": resp.text}


# -----------------------------
# UI
# -----------------------------
uploaded_file = st.file_uploader("Upload a document", type=["pdf", "txt"])
question = st.text_input("Ask a question about the document")

if "extracted_json" not in st.session_state:
    st.session_state.extracted_json = None
if "document_text" not in st.session_state:
    st.session_state.document_text = ""
if "n8n_result" not in st.session_state:
    st.session_state.n8n_result = None


if st.button("Extract Information"):
    if not uploaded_file or not question.strip():
        st.error("Please upload a document and enter a question.")
    else:
        try:
            with st.spinner("Extracting text from document..."):
                document_text = extract_text(uploaded_file)

            if not document_text.strip():
                st.error("No readable text was found in the uploaded document.")
                st.stop()

            with st.spinner("Sending request to Gemini..."):
                result = call_gemini_for_json(document_text, question)

            st.session_state.extracted_json = result
            st.session_state.document_text = document_text
            st.session_state.n8n_result = None

            st.success("Extraction completed.")
            st.subheader("AI Extracted Output")
            st.json(result)

        except Exception as e:
            st.error(f"Request error: {e}")


# -----------------------------
# Stage 3: Optional n8n automation
# -----------------------------
if st.session_state.extracted_json:
    st.divider()
    st.subheader("Send Alert Mail")

    recipient_email = st.text_input(
        "Recipient Email ID",
        placeholder="example@email.com",
        key="recipient_email_input",
    )

    send_clicked = st.button("Send Alert Mail")

    if send_clicked:
        if not recipient_email.strip():
            st.error("Please enter a recipient email ID.")
        elif not N8N_WEBHOOK_URL:
            st.error("Missing N8N_WEBHOOK_URL in .streamlit/secrets.toml")
        else:
            try:
                with st.spinner("Triggering n8n webhook..."):
                    n8n_response = send_to_n8n(
                        webhook_url=N8N_WEBHOOK_URL,
                        document_text=st.session_state.document_text,
                        question=question,
                        extracted_json=st.session_state.extracted_json,
                        recipient_email=recipient_email.strip(),
                    )

                st.session_state.n8n_result = n8n_response
                st.success("n8n workflow completed.")

                st.subheader("Final Analytical Answer")
                final_answer = (
                    n8n_response.get("final_answer")
                    or n8n_response.get("answer")
                    or n8n_response.get("analysis")
                    or "No final answer returned by n8n."
                )
                st.write(final_answer)

                st.subheader("Generated Email Body")
                email_body = (
                    n8n_response.get("email_body")
                    or n8n_response.get("email")
                    or n8n_response.get("body")
                    or "No email body returned by n8n."
                )
                st.write(email_body)

                st.subheader("Email Automation Status")
                status = (
                    n8n_response.get("status")
                    or n8n_response.get("automation_status")
                    or "No status returned by n8n."
                )
                st.info(status)

            except Exception as e:
                st.error(f"n8n request failed: {e}")

    # Show the last n8n response if available
    if st.session_state.n8n_result:
        with st.expander("Raw n8n Response"):
            st.json(st.session_state.n8n_result)

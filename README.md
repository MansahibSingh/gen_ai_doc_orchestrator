AI Document Orchestrator (Resume Analyzer)

Overview:
This project is an AI-powered automation system that extracts structured insights from resumes and delivers results via both UI and email.

Key Features:
- AI-based document understanding
- Structured JSON output
- Automated email delivery
- Real-time API response
- End-to-end workflow automation

Architecture:
Streamlit UI → n8n Webhook → Data Processing → AI Agent → Email → API Response

Workflow:
1. User uploads resume and enters query
2. Webhook receives data
3. Data is processed and formatted
4. AI Agent extracts insights
5. Email is sent to user
6. Response returned to UI

Tech Stack:
- Streamlit
- n8n
- Google Gemini / OpenRouter
- Gmail API
- pdfplumber

Challenges:
- Fixed invalid JSON issues using structured output parser
- Solved email mapping issues
- Handled API rate limits with retries

Use Cases:
- Resume screening
- Document analysis
- Automation pipelines

Future Improvements:
- ATS scoring
- Multi-document support
- RAG integration
- SaaS deployment

Author:
Mansahib Singh


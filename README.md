# AI Document Orchestrator (Resume Analyzer)

An AI-powered automation system that extracts structured insights from resumes and delivers results via both UI and email.

## 📌 Overview

This project is an end-to-end AI workflow automation pipeline that allows users to:

Upload a resume (PDF)
Ask specific queries (e.g., summary, skills, experience)
Get structured insights using AI
Receive results instantly on UI + Email
🧠 Key Features
🤖 AI-based document understanding (LLM-powered)
📊 Structured data extraction (JSON format)
📩 Automated email delivery (Gmail integration)
⚡ Real-time response via API (Webhook → Streamlit)
🔄 Fully automated workflow using n8n
🧩 Modular and scalable architecture
🏗️ Architecture
Streamlit UI → n8n Webhook → Data Processing → AI Agent → Email → API Response
Components:
Frontend: Streamlit
Backend Orchestration: n8n
AI Model: Google Gemini / OpenRouter
Email Service: Gmail API
PDF Processing: pdfplumber
⚙️ Workflow Explanation
1. User Input (Streamlit)
Upload resume
Enter query (e.g., "summary")
Provide email
2. Webhook Trigger (n8n)
Receives request from UI
3. Data Preparation
Extracts:
question
document_text
recipient_email
4. AI Agent
Processes resume text
Returns structured JSON:
{
  "answer": "Summary...",
  "data": {
    "skills": [],
    "experience": []
  }
}
5. Email Automation
Sends formatted report to user
6. API Response
Sends structured output back to Streamlit UI
🖥️ Sample Output
{
  "status": "success",
  "summary": "The candidate has professional experience...",
  "data": { ... },
  "email_sent": true
}
🛠️ Tech Stack
Layer	Technology
Frontend	Streamlit
Backend	n8n
AI Model	Gemini / OpenRouter
Email	Gmail API
Parsing	Structured Output Parser
PDF Handling	pdfplumber
🚧 Challenges & Solutions
❌ Invalid JSON from AI

✔ Fixed using structured output parser + strict prompt engineering

❌ Email not sending

✔ Corrected dynamic field mapping

❌ API rate limits

✔ Switched models + added retry logic

❌ Webhook response errors

✔ Fixed JSON expression formatting

📈 Use Cases
Resume screening (HR Tech)
Document summarization
Business intelligence extraction
Automation pipelines
🔮 Future Improvements
ATS scoring system
Multi-document processing
RAG (Retrieval-Augmented Generation)
Authentication system
SaaS deployment
▶️ How to Run
1. Clone the repository
git clone https://github.com/your-username/ai-document-orchestrator.git
cd ai-document-orchestrator
2. Run Streamlit app
streamlit run app.py
3. Configure n8n
Create webhook
Connect AI Agent
Set Gmail credentials
Add Respond to Webhook node
🧑‍💻 Author

Mansahib Singh
Aspiring Data Analyst | AI & Automation Enthusiast

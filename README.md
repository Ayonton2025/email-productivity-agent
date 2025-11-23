# InboxAI - Email Productivity Agent

![InboxAI](https://img.shields.io/badge/InboxAI-AI%20Powered%20Email-blue)
![Version](https://img.shields.io/badge/version-1.0.0-green)
![License](https://img.shields.io/badge/license-MIT-blue)

## 🚀 Overview

**InboxAI** is an intelligent, prompt-driven email productivity agent that transforms your email management experience using AI-powered automation. Process your inbox with smart categorization, automatic task extraction, intelligent reply drafting, and natural language interaction.

![InboxAI Dashboard](https://via.placeholder.com/800x400/6366f1/ffffff?text=InboxAI+Dashboard)

## ✨ Features

### 🤖 AI-Powered Email Processing
- **Smart Categorization**: Automatically categorizes emails into Important, Newsletter, Spam, To-Do, and more
- **Action Item Extraction**: Identifies tasks, deadlines, and priorities from email content
- **Intelligent Summarization**: Creates concise summaries highlighting key points and required actions
- **Sentiment Analysis**: Understands email tone and urgency levels

### 💬 Interactive AI Assistant
- **Natural Language Chat**: Ask questions about your emails in plain English
- **Context-Aware Responses**: AI understands email context and relationships
- **Smart Suggestions**: Get proactive recommendations for email management
- **Multi-Email Analysis**: Process insights across your entire inbox

### 📝 Smart Draft Management
- **AI-Generated Replies**: Draft professional responses based on email context
- **Tone Customization**: Generate replies in professional, casual, or formal tones
- **Template Management**: Save and reuse successful email templates
- **Safe Draft Storage**: All drafts are saved for review - no automatic sending

### 🧠 Prompt-Driven Intelligence
- **Customizable AI Behavior**: Modify and create prompt templates
- **Category-Specific Prompts**: Different prompts for categorization, summarization, reply drafting
- **Real-time Testing**: Test prompts with sample emails before deployment
- **Version Control**: Track prompt versions and improvements

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │◄──►│   Backend API    │◄──►│   AI Engine     │
│   (React)       │    │   (FastAPI)      │    │   (LLM Service) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User          │    │   Database       │    │   Prompt Brain  │
│   Interface     │    │   (SQLite)       │    │   (Templates)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🛠️ Installation & Setup

### Prerequisites

- **Python 3.8+**
- **Node.js 16+**
- **npm or yarn**
- **Git**

### Quick Start

#### 1. Clone the Repository
```bash
git clone https://github.com/your-username/email-productivity-agent.git
cd email-productivity-agent
```

#### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

**Environment Configuration (.env):**
```env
# API Keys (Optional - for enhanced AI features)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Application Settings
LLM_PROVIDER=mock  # Options: mock, openai, anthropic
DATABASE_URL=sqlite+aiosqlite:///./email_agent.db
DEBUG=true
HOST=0.0.0.0
PORT=8000
SECRET_KEY=your-secret-key-here
```

#### 3. Frontend Setup

```bash
# Open new terminal and navigate to frontend
cd frontend

# Install dependencies
npm install

# Set up environment
cp .env.example .env
```

**Frontend Environment (.env):**
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/ws/agent
```

#### 4. Run the Application

**Start Backend:**
```bash
cd backend
python run.py
```
Backend will be available at: `http://localhost:8000`

**Start Frontend:**
```bash
cd frontend
npm run dev
```
Frontend will be available at: `http://localhost:3000`

## 🎯 Usage Guide

### Getting Started

1. **Load Sample Data**: Click "Load Mock Inbox" to populate the system with sample emails
2. **Explore the Interface**: Familiarize yourself with the four main sections:
   - **Inbox**: View and manage your emails
   - **AI Assistant**: Chat with your email assistant
   - **Drafts**: Create and manage email responses
   - **AI Prompts**: Customize AI behavior

### Managing Emails

#### Viewing and Processing Emails
- Click any email in the inbox to view details
- See AI-generated categories, summaries, and action items
- Use quick actions to archive, star, or reply

#### Using the AI Assistant
```bash
# Example queries you can ask:
"Summarize my latest emails"
"What urgent tasks do I have today?"
"Draft a professional reply to the meeting request"
"Show me all emails from project managers"
"Categorize my unread emails"
```

#### Creating and Managing Drafts
1. Navigate to **Drafts** section
2. Click **New Draft** to create a new email
3. Use AI suggestions or write manually
4. Choose tone: Professional, Casual, or Formal
5. Save drafts for later review

### Customizing AI Behavior

#### Managing Prompt Templates
1. Go to **AI Prompts** section
2. View existing prompt templates
3. Create new prompts for specific use cases
4. Test prompts before activating

#### Example Prompt Customization
```javascript
// Categorization Prompt Example
"You are an email categorization expert. Analyze the email and categorize it as: 
Important, Newsletter, Spam, To-Do, Personal, Work, Finance, or Travel. 
Consider the sender's importance, email content, urgency, and relationship to the recipient."

// Action Extraction Prompt Example  
"Extract all actionable tasks from this email. For each task, identify:
- The specific action required
- Any mentioned deadlines
- Priority level (high/medium/low)
- Person responsible if mentioned
Format as JSON array."
```

## 🔧 API Documentation

### Base URL
```
http://localhost:8000/api/v1
```

### Key Endpoints

#### Email Management
```http
GET    /emails              # Get all emails
POST   /emails/load-mock    # Load mock email data
GET    /emails/{id}         # Get specific email
PUT    /emails/{id}/category # Update email category
```

#### Prompt Management
```http
GET    /prompts             # Get all prompt templates
POST   /prompts             # Create new prompt
PUT    /prompts/{id}        # Update prompt template
```

#### Draft Management
```http
GET    /drafts              # Get all email drafts
POST   /drafts              # Create new draft
```

#### AI Agent
```http
POST   /agent/process       # Process email with specific prompt
WS     /ws/agent           # WebSocket for real-time chat
```

### WebSocket Events

**Connection:**
```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/agent');

// Send chat message
ws.send(JSON.stringify({
  type: 'chat',
  message: 'Summarize my important emails',
  conversation_id: 'unique-id'
}));
```

**Message Types:**
- `chat`: Send chat messages to AI assistant
- `process_email`: Request email processing
- `generate_draft`: Generate email draft

## 🗂️ Project Structure

```
email-productivity-agent/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints.py          # REST API endpoints
│   │   │   └── websockets.py         # WebSocket handlers
│   │   ├── core/
│   │   │   ├── config.py             # Application configuration
│   │   │   └── security.py           # Security utilities
│   │   ├── models/
│   │   │   ├── database.py           # Database models
│   │   │   ├── email_models.py       # Email-related models
│   │   │   └── prompt_models.py      # Prompt templates
│   │   ├── services/
│   │   │   ├── email_service.py      # Email processing logic
│   │   │   ├── llm_service.py        # AI integration
│   │   │   ├── prompt_service.py     # Prompt management
│   │   │   └── agent_service.py      # AI agent logic
│   │   └── utils/
│   │       ├── helpers.py            # Utility functions
│   │       └── validators.py         # Data validation
│   ├── requirements.txt              # Python dependencies
│   └── run.py                       # Application entry point
├── frontend/
│   ├── public/
│   │   ├── index.html               # Main HTML file
│   │   ├── manifest.json            # PWA manifest
│   │   └── mail.svg                 # Application icon
│   ├── src/
│   │   ├── components/
│   │   │   ├── inbox/               # Inbox management components
│   │   │   ├── agent/               # AI assistant components
│   │   │   ├── drafts/              # Draft management components
│   │   │   └── prompts/             # Prompt management components
│   │   ├── context/
│   │   │   ├── EmailContext.jsx     # Email state management
│   │   │   └── PromptContext.jsx    # Prompt state management
│   │   ├── styles/
│   │   │   └── globals.css          # Global styles and design system
│   │   ├── App.jsx                  # Main application component
│   │   └── main.jsx                 # Application entry point
│   ├── package.json                 # Node.js dependencies
│   └── vite.config.js               # Vite configuration
├── data/
│   ├── mock_inbox.json              # Sample email data
│   └── default_prompts.json         # Default AI prompts
└── docs/
    ├── API.md                       # API documentation
    └── SETUP.md                     # Detailed setup guide
```

## 🎨 Customization

### Adding New Email Categories

1. **Update Prompt Templates:**
```python
# In your categorization prompt
NEW_CATEGORIES = "Important, Newsletter, Spam, To-Do, Personal, Work, Finance, Travel, Urgent, Follow-up"
```

2. **Update Frontend Styling:**
```css
/* Add new category styles */
.badge-urgent {
  background: #dc2626;
  color: white;
}

.badge-follow-up {
  background: #7c3aed;
  color: white;
}
```

### Creating Custom AI Prompts

1. Navigate to **AI Prompts** section
2. Click **New Prompt**
3. Define:
   - **Name**: Descriptive name for the prompt
   - **Category**: Purpose (categorization, summary, etc.)
   - **Template**: The actual prompt text with variables
   - **Parameters**: Expected input variables

### Example: Meeting Detection Prompt
```javascript
// Prompt Template
"If this email contains meeting-related content (dates, times, locations, agendas), 
extract the following information in JSON format:
- meeting_topic
- proposed_date
- proposed_time
- location_or_platform
- attendees_mentioned
- preparation_required

If it's not a meeting request, return empty object."
```

## 🔍 Troubleshooting

### Common Issues

**Backend Won't Start:**
```bash
# Check Python version
python --version  # Should be 3.8+

# Check dependencies
pip list | grep fastapi

# Check port availability
netstat -an | grep 8000
```

**Frontend Connection Issues:**
```bash
# Check if backend is running
curl http://localhost:8000/health

# Verify environment variables
cat frontend/.env

# Check browser console for errors
# Press F12 → Console tab
```

**Database Issues:**
```bash
# Reset database
rm backend/email_agent.db
python backend/run.py
```

### Performance Optimization

**For Large Email Volumes:**
```python
# Increase processing batch size
PROCESSING_BATCH_SIZE = 10
MAX_CONCURRENT_REQUESTS = 5
```

**Memory Optimization:**
```javascript
// Frontend lazy loading
const HeavyComponent = React.lazy(() => import('./HeavyComponent'));
```

## 🚀 Deployment

### Production Build

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python run.py
```

**Frontend:**
```bash
cd frontend
npm run build
npm run preview
```

### Docker Deployment

**Dockerfile:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .
COPY data/ ./data/

CMD ["python", "run.py"]
```

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///./email_agent.db
      - LLM_PROVIDER=openai
      - OPENAI_API_KEY=${OPENAI_API_KEY}
  
  frontend:
    build: 
      context: .
      dockerfile: frontend.Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      - backend
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Fork and clone the repository
git clone https://github.com/your-username/email-productivity-agent.git

# Create feature branch
git checkout -b feature/amazing-feature

# Make changes and test
# Submit pull request
```

### Code Style
- Follow PEP 8 for Python code
- Use ESLint for JavaScript/React
- Write comprehensive docstrings
- Include tests for new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FastAPI** for the excellent web framework
- **React** and **Vite** for the modern frontend tooling
- **Tailwind CSS** for the utility-first CSS framework
- **Lucide React** for the beautiful icons
- **OpenAI** for AI capabilities inspiration

## 📞 Support

- **Documentation**: [Docs](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-username/email-productivity-agent/issues)
- **Email**: support@inboxai.example.com

## 🗺️ Roadmap

### Upcoming Features
- [ ] Real email integration (Gmail, Outlook)
- [ ] Advanced OpenAI integration
- [ ] Team collaboration features
- [ ] Mobile app
- [ ] Advanced analytics dashboard
- [ ] Email scheduling
- [ ] Template library
- [ ] Integration with project management tools

### Version History
- **v1.0.0** (Current): Initial release with core AI email management features
- **v1.1.0** (Planned): Real email provider integration
- **v1.2.0** (Planned): Advanced AI features and team collaboration

---

<div align="center">

**InboxAI** - Transform your email workflow with AI intelligence ✨

[Getting Started](#installation--setup) • [Features](#-features) • [API Docs](#-api-documentation)

</div>
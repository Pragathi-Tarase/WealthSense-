WealthSense - Indian Portfolio Management & AI Intelligence Platform
WealthSense is a premium, single-page application (SPA) designed for the modern Indian investor. It provides real-time market insights, unified portfolio tracking, and AI-driven financial analysis using a robust FastAPI backend and a high-performance Vanilla JS/CSS frontend.

🚀 Key Features
📈 Market & Portfolio
Real-Time Price Feed: Live data for Indian stocks (Nifty/Sensex) with mock fallbacks for rate-limit protection.
Unified Dashboard: View consolidated insights from connected brokers or uploaded statements.
CAS Statement Processing: Support for Consolidated Account Statement (CAS) file uploads to track historical holdings.
TradingView Integration: Professional-grade interactive charts for detailed technical analysis.
🤖 AI-Powered Intelligence (Gemini Integration)
AI News Sentiment: Real-time analysis of stock news with dynamic Bullish/Bearish/Neutral classification.
AI Portfolio Analyst: Personalized "Health Check" reports that analyze holding performance and suggest rebalancing.
Full-Context AI Chatbot: A market expert that answers questions with real-time knowledge of your specific portfolio and current market trends.
🔐 Security & Identity
JWT-Based Authentication: Secure, stateless user sessions with token rotation.
KYC & Identity Verification: Integrated PAN/Demat verification flow with secure OTP delivery.
Premium UI: Glassmorphic design with smooth micro-animations and dark mode optimized for visual clarity.

🛠 Tech Stack
Component	Technology
Backend	    Python 3.10+, FastAPI
Frontend	HTML5, Vanilla JavaScript, Modern CSS       (Glassmorphism)
Database	MongoDB (Production), In-memory (Development/Mock)
AI / LLM	Google Gemini (Gemini Flash), OpenAI (Optional)
Charts	TradingView (TV.js)
Auth	JWT (python-jose), OTP Simulation

📂 Project Structure
WEALTHSENSE/
├── backend/
│   ├── routes/             # API Endpoints (Chat, News, Market, Dashboard, etc.)
│   ├── services/           # Business Logic (AI, Stock API, User Management)
│   ├── database/           # MongoDB Connection & Schemas
│   ├── main.py             # FastAPI Entry Point & App Config
│   ├── config.py           # Environment Variable Management
│   ├── models.py           # Pydantic Data Models
│   └── requirements.txt    # Python Dependencies
├── frontend/
│   ├── assets/             # Images, Icons, Logos
│   ├── index.html          # Landing Page
│   ├── dashboard.html      # Main Application UI
│   ├── intro.html          # Animated Splash Screen
│   └── login.html          # Auth Portal
├── users.json              # Mock database for quick deployment
└── .env                    # (Generated) Local environment secrets

🧪 Dependencies
Core dependencies used in the project:

fastapi & uvicorn: High-performance API framework and server.
google-generativeai: Integration with Google Gemini for sentient analysis.
PyJWT & python-jose: Secure session management.
requests & httpx: Asynchronous/Synchronous handling of external market APIs.
motor & pymongo: Non-blocking MongoDB integration for high-concurrency data access.
python-dotenv: Secure management of API keys and secrets.

⚙️ Environment Configuration
Create a 
.env
 file in the backend/ directory.
 # Core API Keys
GEMINI_API_KEY=your_gemini_api_key
ALPHA_VANTAGE_API_KEY=your_market_data_key
NEWSAPI_API_KEY=your_news_api_key

# Security
APP_SECRET_KEY=generated_high_entropy_key
JWT_ALGORITHM=HS256

# Broker OAuth (Optional)
KITE_API_KEY=your_kite_key
KITE_API_SECRET=your_kite_secret

# Database
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=wealthsense

🛠 Installation & Setup
1. Prerequisites
Python 3.10 or higher
Node.js (Optional, for Live Server)
MongoDB (Running locally or on Atlas)
2. Backend Setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # Add your API keys here
3. Run the Development Server
uvicorn main:app --reload --app-dir backend
4. Frontend Access
The frontend consists of static files. You can serve them using any static host (e.g., Live Server in VS Code):

Open 
frontend/intro.html
 in your browser.
Default API Base: http://127.0.0.1:8000

🏗 Architecture & Data Flow
Frontend: Built with Vanilla components to minimize bundle size and latency. It communicates with the backend via a centralized 
apiCall()
 helper that handles JWT injection.
Backend: Follows a Controller-Service pattern. Routes (routes/) handle HTTP logic, while Services (services/) handle data processing, AI interactions, and external API fetching.
AI Context: Every AI request automatically gathers the user's latest portfolio holdings and market status, injecting it into the prompt to provide accurate, data-driven financial advice.

🛡 Security Considerations
CORS Management: Backend headers are restricted to authorized origins.
Input Validation: All API inputs are strictly typed using Pydantic models.
API Key Masking: Sensitive keys are kept in 
.env
 and never exposed to the client; all AI and external data calls are proxied through the backend.

🤝 Contribution Guidelines
Branching: Use feature/ for new tools and fix/ for bug repairs.
Testing: Run local tests for AI connectivity via specialized scripts (e.g., 
test_chat_context.py
).
Code Style: Follow PEP8 for backend Python and standard ES6+ practices for frontend JS.

⚖️ License
This project is licensed under the MIT License - see the LICENSE file for details.

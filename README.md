# GreenRoute
 
GreenRoute is an AI-powered carbon footprint management app that helps you travel sustainably. Chat with an AI agent to generate personalized travel packages comparing eco-friendly and standard options, track your annual carbon budget, and earn reward points every time you choose the greener path.

## Getting Started
 
These instructions will guide you on how to set up and run GreenRoute locally for development and testing purposes.

### Prerequisites
 
To run GreenRoute, you will need:
 
- Node.js and npm for the frontend
- Python 3.10+ and pip for the backend

### Installing
 
Follow these steps to get your development environment running:

#### Backend
 
1. Clone the repository and navigate to the backend directory:
  ```bash
  cd backend
  ```
 
2. Create and activate a virtual environment:
  ```bash
  python -m venv venv
  source venv/bin/activate        # macOS / Linux
  .\venv\Scripts\activate         # Windows
  ```
 
3. Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```
 
4. Start the FastAPI server:
  ```bash
  python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
  ```
 

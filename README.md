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

 #### Frontend
 
1. Navigate to the frontend directory:
  ```bash
  cd frontend
  ```
 
2. Install dependencies:
  ```bash
  npm install
  ```
 
3. Start the Vite dev server:
  ```bash
  npm run dev
  ```

4. Start the FastAPI server:
  ```bash
  python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
  ```
 
#### Run Both at Once
 
From the project root, use the provided launch scripts:
 
```bash
./run.sh    # macOS / Linux
.\run.ps1   # Windows PowerShell
```
 
This starts the FastAPI backend (port 8000) and the Vite frontend simultaneously and also launches the Arize Phoenix observability console at http://localhost:6006.

### Configuration
 
Before running the application, you will need a Google Gemini API key.
 
1. Create a `.env` file inside the `backend/` directory:
  ```plaintext
  # backend/.env
  GEMINI_API_KEY=your_gemini_api_key_here
  ```
 
2. Optionally, configure a PostgreSQL database (defaults to local SQLite if not set):
  ```plaintext
  DATABASE_URL=your_postgres_connection_string
  # or individually:
  POSTGRES_HOST=your_host
  POSTGRES_USER=your_user
  POSTGRES_PASSWORD=your_password
  POSTGRES_DB=your_database
  ```
 
3. For cloud deployments (e.g., Google Cloud Run), set the following additional variable:
  ```plaintext
  PHOENIX_COLLECTOR_ENDPOINT=your_phoenix_collector_url
  ```

## Built With
 
- **Frontend**: React 19, Vite, Lucide React
- **Backend**: FastAPI, Python, Uvicorn
- **APIs**: Google Places API, Google Geocoding API, AviationStack
- **AI**: Google AI Studio & Google Gemini 2.5 Flash
- **Database**: Google Cloud SQL (production)
- **Hosting & Infrastructure**: Google Cloud Run, Firebase Hosting
- **Maps & Travel**: Google Maps API, Google Travel API
- **Observability**: Arize Phoenix, OpenTelemetry, OpenInference

## Contributing
 
If you're interested in contributing to GreenRoute, please read through the project files and reach out to the team to see how you can help.

### Main Authors
 
- **Sahasra Kalakonda** - _Initial work_ - [sahasrakalakonda16@gmail.com](mailto:sahasrakalakonda16@gmail.com)
- **Tanvi Sathish Arvind** - _Initial work_ - [tanvi.s.arvind@gmail.com](mailto:tanvi.s.arvind@gmail.com)
- **Strider Zimmerman** - _Initial work_ - [Strider.zimmerman@icloud.com](mailto:Strider.zimmerman@icloud.com)

## Acknowledgments
 
- Thanks to Google for the Gemini API powering the AI agent.
- Thanks to Arize AI for Phoenix observability tooling.
- Thanks to all open-source contributors behind FastAPI, Vite, and React.

## License
 
This project is licensed under the MIT License — see the LICENSE file in the repository for more details.


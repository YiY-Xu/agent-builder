# Agent Builder

A tool for building agents with Claude. This application allows users to create custom agent configurations through a conversational interface with Claude, and export them as YAML files for use in agent frameworks.

## Project Structure

The project is divided into two main parts:

- **Frontend**: A React-based single-page application that provides the user interface
- **Backend**: A Python FastAPI service that handles communication with Claude

## Features

- Dual-panel interface with chat on the left and agent configuration on the right
- Conversational agent creation guided by Claude
- Real-time configuration updates as the conversation progresses
- YAML generation and export
- Docker support for easy deployment

## Getting Started

### Prerequisites

- Node.js (v16+)
- Python (v3.9+)
- Claude API key

### Environment Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/agent-builder.git
cd agent-builder
```

2. Create a `.env` file in the `backend` directory with your Claude API key:
```
CLAUDE_API_KEY=your_claude_api_key_here
```

### Running the Backend

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the FastAPI server:
```bash
uvicorn app.main:app --reload
```

The backend will be available at `http://localhost:8000`.

### Running the Frontend

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm start
```

The frontend will be available at `http://localhost:3000`.

### Using Docker

You can also run the entire application using Docker Compose:

1. Ensure Docker and Docker Compose are installed
2. Set your Claude API key in the environment:
```bash
export CLAUDE_API_KEY=your_claude_api_key_here
```
3. Start the services:
```bash
cd docker
docker-compose up
```

## Usage

1. Open the application in your browser
2. Begin the conversation with Claude in the left panel
3. Follow Claude's guidance to create your agent
4. Watch as the configuration updates in the right panel
5. Once complete, download the generated YAML file

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
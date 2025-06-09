# Side-Stacker Game

## Project Overview
The Side-Stacker Game is a multiplayer game that allows players to compete against each other or an AI bot. The project is divided into two main parts:

1. **Backend**: Built using Django and Django Channels, it provides REST APIs and WebSocket support for real-time gameplay.
2. **Frontend**: Developed with React, it offers an interactive user interface for players to create, join, and play games.

## Project Structure
```
side-stacker-game/
├── backend/
│   ├── api/                # REST API for game management
│   ├── game/               # Game logic, AI bot, and WebSocket consumers
│   ├── side_stacker_backend/ # Django project settings and ASGI configuration
│   └── db.sqlite3          # SQLite database
├── frontend/
│   ├── public/             # Static files
│   ├── src/                # React components, services, and store
│   └── package.json        # Frontend dependencies
└── ReadME.md               # Project documentation
```

## Installation

### Backend Setup
1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Apply migrations:
   ```bash
   python manage.py migrate
   ```
5. Start the development server:
   ```bash
   python -m daphne -p 8000 side_stacker_backend.asgi:application 
   ```

### Frontend Setup
1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm start
   ```

## Backend Endpoints

### REST API
- **Create Game**: `POST /api/games/`
- **Get Game**: `GET /api/games/<game_id>/`
- **Join Game**: `POST /api/games/<game_id>/join/`
- **AI Move**: `POST /api/games/<game_id>/ai-move/`

### WebSocket
- **Game Updates**: Real-time updates for game state and player actions.

## Features Implemented

### Backend
- Game creation and management.
- AI bot with multiple difficulty levels (Easy, Medium, Hard).
- WebSocket support for real-time gameplay.
- REST API for game state retrieval and updates.

### Frontend
- Interactive UI for creating and joining games.
- Real-time game board updates using WebSocket.
- Support for Player vs Player and Player vs AI modes.

## Future Enhancements
- Add user authentication.
- Improve AI bot strategies.
- Deploy the application to a cloud platform.

## Contributing
Contributions are welcome! Please fork the repository and submit a pull request for any enhancements or bug fixes.
import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { createGame, joinGame } from '../store/gameSlice';

const GameMenu = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { loading, error } = useSelector(state => state.game);
  
  const [gameMode, setGameMode] = useState('pvp');
  const [difficulty, setDifficulty] = useState('easy');
  const [playerName, setPlayerName] = useState('');
  const [joinGameId, setJoinGameId] = useState('');

  const handleCreateGame = async () => {
    try {
      const gameData = {
        mode: gameMode,
        difficulty: gameMode === 'pva' ? difficulty : 'easy',
        player1_name: playerName || 'Player 1',
        player2_name: gameMode === 'pva' ? 'AI Bot' : 'Player 2'
      };
      
      const result = await dispatch(createGame(gameData));
      if (result.payload && result.payload.game_id) {
        localStorage.setItem(`game_${result.payload.game_id}_player_name`, playerName || 'Player 1');
        navigate(`/game/${result.payload.game_id}`);
      }
    } catch (error) {
      console.error('Error creating game:', error);
    }
  };

  const handleJoinGame = async () => {
    if (!joinGameId) return;
    
    try {
      // const result = await dispatch(joinGame({
      //   gameId: joinGameId,
      //   playerName: playerName || 'Player 2'
      // }));
      
      navigate(`/game/${joinGameId}?join=${encodeURIComponent(playerName || 'Player 2')}`);
    } catch (error) {
      console.error('Error joining game:', error);
    }
  };

  return (
    <div className="game-menu">
      <div className="menu-section">
        <h2>Create New Game</h2>
        
        <div className="form-group">
          <label>Your Name:</label>
          <input
            type="text"
            value={playerName}
            onChange={(e) => setPlayerName(e.target.value)}
            placeholder="Enter your name"
          />
        </div>

        <div className="form-group">
          <label>Game Mode:</label>
          <select value={gameMode} onChange={(e) => setGameMode(e.target.value)}>
            <option value="pvp">Player vs Player</option>
            <option value="pva">Player vs AI</option>
          </select>
        </div>

        {gameMode === 'pva' && (
          <div className="form-group">
            <label>AI Difficulty:</label>
            <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>
        )}

        <button onClick={handleCreateGame} disabled={loading}>
          {loading ? 'Creating...' : 'Create Game'}
        </button>
      </div>

      <div className="menu-section">
        <h2>Join Existing Game</h2>
        
        <div className="form-group">
          <label>Game ID:</label>
          <input
            type="text"
            value={joinGameId}
            onChange={(e) => setJoinGameId(e.target.value)}
            placeholder="Enter game ID"
          />
        </div>

        <button onClick={handleJoinGame} disabled={loading || !joinGameId}>
          Join Game
        </button>
      </div>

      {error && <div className="error">{error}</div>}
    </div>
  );
};

export default GameMenu;

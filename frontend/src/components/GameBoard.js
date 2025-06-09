// Updated GameBoard with proper player identification and move restrictions
import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { getGame, requestAiMove, resetGame, setConnected } from '../store/gameSlice';
import websocketService from '../services/websocket';

const GameBoard = () => {
  const { gameId } = useParams();
  const [searchParams] = useSearchParams();
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const {
    board,
    currentPlayer,
    status,
    winner,
    mode,
    player1Name,
    player2Name,
    connected,
    error,
    currentClientPlayer, // Which player this client represents
    canMove // Whether this client can make moves
  } = useSelector(state => state.game);

  useEffect(() => {
    if (gameId) {
      dispatch(getGame(gameId));

      const joinPlayerName = searchParams.get('join');
      const isJoining = !!joinPlayerName;

      if (!websocketService.isConnected()) {
        if (isJoining) {
          // This is player 2 joining via invite link
          websocketService.connect(gameId, dispatch, joinPlayerName, false);
        } else {
          // This is likely the creator or someone accessing directly
          const storedPlayerName = localStorage.getItem(`game_${gameId}_player_name`) || 'Player 1';
          websocketService.connect(gameId, dispatch, storedPlayerName, true);
        }
      }

      // Set connection status
      dispatch(setConnected(true));
    }
  
    return () => {
      if (process.env.NODE_ENV === 'production') {
        websocketService.disconnect();
        dispatch(setConnected(false));
      }
    };
  }, [gameId, dispatch, searchParams]);

  useEffect(() => {
    if (!connected) return;

    const prevStatus = localStorage.getItem(`game_${gameId}_status`);
    
    if (status === 'finished' && prevStatus === 'active') {
      setTimeout(() => {
        if (winner === null) {
          alert('Game ended in a draw!');
        } else {
          const winnerName = winner === 1 ? player1Name : player2Name;
          alert(`🎉 ${winnerName} wins the game!`);
        }
      }, 100);
    }

    localStorage.setItem(`game_${gameId}_status`, status);
    
  }, [status, winner, player1Name, player2Name, gameId, connected]);

  const handleCellClick = (row, side) => {
    // Enhanced move validation with proper player identification
    if (status !== 'active' || !connected || !canMove) {
      console.log('Move blocked:', { status, connected, canMove, currentClientPlayer, currentPlayer });
      return;
    }
    
    // Additional check for PvA mode
    if (mode === 'pva' && currentPlayer !== 1) {
      console.log('AI turn, player cannot move');
      return;
    }
    
    // Check if current client is the current player
    if (currentClientPlayer !== currentPlayer) {
      console.log(`Not your turn. You are player ${currentClientPlayer}, current turn is player ${currentPlayer}`);
      return;
    }
    
    websocketService.sendMove(row, side, currentPlayer);
  };

  const handleNewGame = () => {
    localStorage.removeItem(`game_${gameId}_status`);
    dispatch(resetGame());
    navigate('/');
  };

  const gameBoard = board && Array.isArray(board) && board.length === 7 
    ? board 
    : Array(7).fill().map(() => Array(7).fill(null));

  const renderCell = (row, col) => {
    const value = gameBoard[row][col];
    let cellClass = 'cell';
    
    if (value === 1) cellClass += ' player1';
    else if (value === 2) cellClass += ' player2';
    
    return (
      <div key={`${row}-${col}`} className={cellClass}>
        {value === 1 ? 'X' : value === 2 ? 'O' : ''}
      </div>
    );
  };

  const canPlayOnSide = (row, side) => {
    if (side === 'L') {
        for (let col = 0; col < 7; col++) {
            if (row[col] === null) {
                return true;
            }
        }
        return false;
    } else {
        for (let col = 6; col >= 0; col--) {
            if (row[col] === null) {
                return true;
            }
        }
        return false;
    }
  };

  const renderRow = (rowIndex) => {
    const row = gameBoard[rowIndex];
    const canPlayLeft = canPlayOnSide(row, 'L');
    const canPlayRight = canPlayOnSide(row, 'R');
    
    return (
      <div key={rowIndex} className="board-row">
        <button
          className={`side-button left ${canPlayLeft && canMove ? 'active' : 'disabled'}`}
          onClick={() => handleCellClick(rowIndex, 'L')}
          disabled={!canPlayLeft || !canMove}
        >
          L
        </button>
        
        <div className="row-cells">
          {row.map((_, colIndex) => renderCell(rowIndex, colIndex))}
        </div>
        
        <button
          className={`side-button right ${canPlayRight && canMove ? 'active' : 'disabled'}`}
          onClick={() => handleCellClick(rowIndex, 'R')}
          disabled={!canPlayRight || !canMove}
        >
          R
        </button>
      </div>
    );
  };

  const getStatusMessage = () => {
    if (status === 'finished') {
      if (winner === null) return 'Game ended in a draw!';
      return `${winner === 1 ? player1Name : player2Name} wins!`;
    }
    
    if (status === 'waiting') return 'Waiting for another player...';
    
    if (status === 'active') {
      const currentPlayerName = currentPlayer === 1 ? player1Name : player2Name;
      const isYourTurn = currentClientPlayer === currentPlayer;
      return `${currentPlayerName}'s turn ${isYourTurn ? '(Your turn!)' : ''}`;
    }
    
    return '';
  };

  return (
    <div className="game-board">
      <div className="game-header">
        <h2>Game #{gameId}</h2>
        <div className="game-info">
          <div>Mode: {mode === 'pvp' ? 'Player vs Player' : 'Player vs AI'}</div>
          <div>Status: {getStatusMessage()}</div>
          <div>You are: {currentClientPlayer ? `Player ${currentClientPlayer}` : 'Not assigned'}</div>
          <div>Connection: {connected ? 'Connected' : 'Disconnected'}</div>
        </div>
      </div>

      <div className="players-info">
        <div className={`player-info ${currentPlayer === 1 ? 'active' : ''} ${currentClientPlayer === 1 ? 'you' : ''}`}>
          {player1Name} (X) {currentClientPlayer === 1 ? '(You)' : ''}
        </div>
        <div className={`player-info ${currentPlayer === 2 ? 'active' : ''} ${currentClientPlayer === 2 ? 'you' : ''}`}>
          {player2Name} (O) {currentClientPlayer === 2 ? '(You)' : ''}
        </div>
      </div>

      <div className="board">
        {gameBoard.map((_, rowIndex) => renderRow(rowIndex))}
      </div>

      <div className="game-controls">
        <button onClick={handleNewGame}>New Game</button>
      </div>

      {error && <div className="error">{error}</div>}
    </div>
  );
};

export default GameBoard;

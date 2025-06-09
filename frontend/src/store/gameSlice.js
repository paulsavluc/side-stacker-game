// Updated game slice with player identification and better state management
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

const API_BASE_URL = 'http://localhost:8000';

const initialState = {
  gameId: null,
  board: Array(7).fill().map(() => Array(7).fill(null)),
  currentPlayer: 1,
  status: 'waiting',
  winner: null,
  mode: 'pvp',
  player1Name: 'Player 1',
  player2Name: 'Player 2',
  connected: false,
  error: null,
  loading: false,
  // New fields for player identification
  currentClientPlayer: null, // Which player number this client represents (1 or 2)
  clientPlayerId: null, // Unique client identifier
  canMove: false // Whether current client can make a move
};

// Enhanced async thunks
export const createGame = createAsyncThunk(
  'game/createGame',
  async (gameData) => {
    const response = await fetch(`${API_BASE_URL}/api/games/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(gameData)
    });
    return response.json();
  }
);

export const getGame = createAsyncThunk(
  'game/getGame',
  async (gameId) => {
    const response = await fetch(`${API_BASE_URL}/api/games/${gameId}/`);
    return response.json();
  }
);

export const requestAiMove = createAsyncThunk(
  'game/requestAiMove',
  async (gameId) => {
    const response = await fetch(`${API_BASE_URL}/api/games/${gameId}/ai-move/`, {
      method: 'POST'
    });
    return response.json();
  }
);

const gameSlice = createSlice({
  name: 'game',
  initialState,
  reducers: {
    updateGameState: (state, action) => {
      const gameData = action.payload;
      state.board = gameData.board || state.board;
      state.currentPlayer = gameData.current_player;
      state.status = gameData.status;
      state.winner = gameData.winner;
      state.player1Name = gameData.player1_name;
      state.player2Name = gameData.player2_name;
      state.mode = gameData.mode;
      
      // Update move permission based on current player and client player
      state.canMove = state.currentClientPlayer === state.currentPlayer && 
                     state.status === 'active' && 
                     state.connected;
    },
    
    setCurrentClientPlayer: (state, action) => {
      state.currentClientPlayer = action.payload.playerNumber;
      state.clientPlayerId = action.payload.playerId;
      
      // Update move permission
      state.canMove = state.currentClientPlayer === state.currentPlayer && 
                     state.status === 'active' && 
                     state.connected;
    },
    
    setConnected: (state, action) => {
      state.connected = action.payload;
      
      // Update move permission
      state.canMove = state.currentClientPlayer === state.currentPlayer && 
                     state.status === 'active' && 
                     state.connected;
    },
    
    setConnectionError: (state, action) => {
      state.error = action.payload;
      state.connected = false;
      state.canMove = false;
    },
    
    resetGame: (state) => {
      return { ...initialState };
    }
  },
  
  extraReducers: (builder) => {
    builder
      .addCase(createGame.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createGame.fulfilled, (state, action) => {
        state.loading = false;
        state.gameId = action.payload.game_id;
      })
      .addCase(createGame.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      })
      .addCase(getGame.fulfilled, (state, action) => {
        const gameData = action.payload;
        state.gameId = gameData.id;
        state.board = gameData.board;
        state.currentPlayer = gameData.current_player;
        state.status = gameData.status;
        state.winner = gameData.winner;
        state.player1Name = gameData.player1_name;
        state.player2Name = gameData.player2_name;
        state.mode = gameData.mode;
      })
      .addCase(requestAiMove.fulfilled, (state, action) => {
        // AI move response will come through WebSocket
      });
  }
});

export const { 
  updateGameState, 
  setCurrentClientPlayer, 
  setConnected, 
  setConnectionError, 
  resetGame 
} = gameSlice.actions;

export default gameSlice.reducer;

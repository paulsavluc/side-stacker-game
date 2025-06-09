import { createSlice } from '@reduxjs/toolkit';

const authSlice = createSlice({
  name: 'auth',
  initialState: {
    currentPlayerName: null,
    playerNumber: null, // 1 or 2
  },
  reducers: {
    setCurrentPlayer: (state, action) => {
      state.currentPlayerName = action.payload.name;
      state.playerNumber = action.payload.number;
    },
    clearCurrentPlayer: (state) => {
      state.currentPlayerName = null;
      state.playerNumber = null;
    },
  },
});

export const { setCurrentPlayer, clearCurrentPlayer } = authSlice.actions;
export default authSlice.reducer;

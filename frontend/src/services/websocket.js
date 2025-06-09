// Updated websocket service with better connection management and player identification
class WebSocketService {
  constructor() {
    this.socket = null;
    this.gameId = null;
    this.dispatch = null;
    this.playerName = null;
    this.playerId = null; // Add player identification
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectInterval = 3000;
  }

  connect(gameId, dispatch, playerName = null, isCreator = false) {
    this.gameId = gameId;
    this.dispatch = dispatch;
    this.playerName = playerName;
    this.isCreator = isCreator;
    
    // Generate unique player ID for session tracking
    this.playerId = this.generatePlayerId();
    
    const wsUrl = `ws://localhost:8000/ws/game/${gameId}/`;
    this.socket = new WebSocket(wsUrl);

    this.socket.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      
      // const storedPlayerName = localStorage.getItem(`game_${gameId}_player_name`) || playerName;
      // Only send join_game if there's a player name and it's not just a creator connecting
      if (playerName && !isCreator) {
        this.sendJoinGame(playerName);
        localStorage.setItem(`game_${gameId}_player_name`, playerName);
      } else if (playerName && isCreator) {
        // For creators, send a special creator join message
        this.sendCreatorJoin(playerName);
        localStorage.setItem(`game_${gameId}_player_name`, playerName);
      } else {
        // This is a reconnection
        const storedPlayerName = localStorage.getItem(`game_${gameId}_player_name`);
        if (storedPlayerName) {
          this.sendRejoinGame(storedPlayerName);
        }
      }
    };

    this.socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('WebSocket message received:', data);
      
      if (data.type === 'game_update') {
        this.dispatch({
          type: 'game/updateGameState',
          payload: data.game_data
        });
      } else if (data.type === 'player_joined') {
        this.dispatch({
          type: 'game/updateGameState',
          payload: data.game_data
        });
      } else if (data.type === 'player_assignment') {
        // Store which player this client represents
        this.dispatch({
          type: 'game/setCurrentClientPlayer',
          payload: {
            playerNumber: data.player_number,
            playerId: this.playerId
          }
        });
      }
    };

    this.socket.onclose = () => {
      console.log('WebSocket disconnected');
      this.handleReconnection();
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  sendCreatorJoin(playerName) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.playerName = playerName;
      this.socket.send(JSON.stringify({
        action: 'creator_join',
        player_name: playerName,
        player_id: this.playerId
      }));
    }
  }

  // Enhanced reconnection logic
  handleReconnection() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      
      setTimeout(() => {
        if (this.gameId && this.dispatch) {
          this.connect(this.gameId, this.dispatch, this.playerName);
        }
      }, this.reconnectInterval);
    } else {
      console.error('Max reconnection attempts reached');
      this.dispatch({
        type: 'game/setConnectionError',
        payload: 'Connection lost. Please refresh the page.'
      });
    }
  }

  sendJoinGame(playerName) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.playerName = playerName;
      this.socket.send(JSON.stringify({
        action: 'join_game',
        player_name: playerName,
        player_id: this.playerId
      }));
    }
  }

  // Update sendRejoinGame to include player name
  sendRejoinGame(playerName = null) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({
        action: 'rejoin_game',
        player_id: this.playerId,
        player_name: playerName || this.playerName
      }));
    }
  }

  sendMove(row, side, player) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({
        action: 'make_move',
        row,
        side,
        player,
        player_id: this.playerId
      }));
    }
  }

  generatePlayerId() {
    return `player_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  isConnected() {
    return this.socket && this.socket.readyState === WebSocket.OPEN;
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}

export default new WebSocketService();

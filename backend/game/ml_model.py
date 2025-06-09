import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pickle
import os
from django.conf import settings
import logging
import random
from collections import deque

logger = logging.getLogger(__name__)

class SideStackerNet(nn.Module):
    """
    Neural Network for Side-Stacker game
    Input: 7x7 board state + available moves
    Output: Move probabilities
    """
    def __init__(self):
        super(SideStackerNet, self).__init__()
        
        # Board analysis layers
        self.board_conv = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),  # 3 channels: empty, player1, player2
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 32, kernel_size=3, padding=1),
            nn.ReLU(),
        )
        
        # Flatten and combine with move encoding
        self.fc_layers = nn.Sequential(
            nn.Linear(32 * 7 * 7 + 14, 512),  # Board features + move encoding (7 rows * 2 sides)
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 14)  # 7 rows * 2 sides = 14 possible moves
        )
        
    def forward(self, board_state, available_moves_mask):
        # Process board through conv layers
        x = self.board_conv(board_state)
        x = x.view(x.size(0), -1)  # Flatten
        
        # Concatenate with available moves
        x = torch.cat([x, available_moves_mask], dim=1)
        
        # Get move probabilities
        move_probs = self.fc_layers(x)
        
        # Apply softmax only to available moves
        masked_probs = move_probs + (available_moves_mask - 1) * 1e9  # Large negative for unavailable moves
        return torch.softmax(masked_probs, dim=1)

class SideStackerMLAgent:
    """
    ML Agent for Side-Stacker game with training capabilities
    """
    def __init__(self, model_path=None):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = SideStackerNet().to(self.device)
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        self.criterion = nn.MSELoss()
        
        # Training data storage
        self.memory = deque(maxlen=10000)
        self.training_games = 0
        
        # Load existing model if available
        self.model_path = model_path or os.path.join(settings.BASE_DIR, 'game', 'ml_models', 'sidestacker_model.pth')
        self.load_model()
        
    def board_to_tensor(self, board):
        """
        Convert board state to tensor format
        """
        # Create 3-channel representation
        tensor = np.zeros((3, 7, 7), dtype=np.float32)
        
        for i in range(7):
            for j in range(7):
                if board[i][j] is None:
                    tensor[0][i][j] = 1  # Empty channel
                elif board[i][j] == 1:
                    tensor[1][i][j] = 1  # Player 1 channel
                elif board[i][j] == 2:
                    tensor[2][i][j] = 1  # Player 2 channel
        
        return torch.FloatTensor(tensor).unsqueeze(0).to(self.device)
    
    def moves_to_tensor(self, available_moves):
        """
        Convert available moves to tensor format
        """
        moves_mask = np.zeros(14, dtype=np.float32)
        
        for row, side in available_moves:
            move_idx = row * 2 + (0 if side == 'L' else 1)
            moves_mask[move_idx] = 1
        
        return torch.FloatTensor(moves_mask).unsqueeze(0).to(self.device)
    
    def tensor_to_move(self, move_tensor, available_moves):
        """
        Convert tensor output back to move format
        """
        move_probs = move_tensor.cpu().numpy().flatten()
        
        # Create list of (probability, move) pairs for available moves
        move_options = []
        for row, side in available_moves:
            move_idx = row * 2 + (0 if side == 'L' else 1)
            move_options.append((move_probs[move_idx], (row, side)))
        
        # Sort by probability and return best move
        move_options.sort(reverse=True, key=lambda x: x[0])
        return move_options[0][1] if move_options else None
    
    def predict_move(self, board, available_moves, use_exploration=False):
        """
        Predict the best move using the trained model
        """
        if not available_moves:
            return None
        
        try:
            self.model.eval()
            with torch.no_grad():
                board_tensor = self.board_to_tensor(board)
                moves_tensor = self.moves_to_tensor(available_moves)
                
                move_probs = self.model(board_tensor, moves_tensor)
                
                if use_exploration and random.random() < 0.1:  # 10% exploration
                    return random.choice(available_moves)
                
                return self.tensor_to_move(move_probs, available_moves)
                
        except Exception as e:
            logger.error(f"ML prediction error: {e}")
            return random.choice(available_moves)
    
    def add_training_data(self, board, available_moves, chosen_move, reward):
        """
        Add training data to memory
        """
        board_tensor = self.board_to_tensor(board).cpu()
        moves_tensor = self.moves_to_tensor(available_moves).cpu()
        
        # Convert chosen move to target tensor
        target = np.zeros(14, dtype=np.float32)
        if chosen_move:
            row, side = chosen_move
            move_idx = row * 2 + (0 if side == 'L' else 1)
            target[move_idx] = reward
        
        self.memory.append((board_tensor, moves_tensor, torch.FloatTensor(target)))
    
    def train_step(self, batch_size=32):
        """
        Perform one training step
        """
        if len(self.memory) < batch_size:
            return
        
        # Sample batch from memory
        batch = random.sample(self.memory, batch_size)
        
        board_batch = torch.cat([item[0] for item in batch]).to(self.device)
        moves_batch = torch.cat([item[1] for item in batch]).to(self.device)
        target_batch = torch.stack([item[2] for item in batch]).to(self.device)
        
        # Forward pass
        self.model.train()
        predictions = self.model(board_batch, moves_batch)
        
        # Calculate loss
        loss = self.criterion(predictions, target_batch)
        
        # Backward pass
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        return loss.item()
    
    def save_model(self):
        """
        Save the trained model
        """
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            torch.save({
                'model_state_dict': self.model.state_dict(),
                'optimizer_state_dict': self.optimizer.state_dict(),
                'training_games': self.training_games
            }, self.model_path)
            logger.info(f"Model saved to {self.model_path}")
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def load_model(self):
        """
        Load existing model if available
        """
        try:
            if os.path.exists(self.model_path):
                checkpoint = torch.load(self.model_path, map_location=self.device)
                self.model.load_state_dict(checkpoint['model_state_dict'])
                self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
                self.training_games = checkpoint.get('training_games', 0)
                logger.info(f"Model loaded from {self.model_path}")
            else:
                logger.info("No existing model found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading model: {e}")

# Global ML agent instance
ml_agent = None

def get_ml_agent():
    """
    Get or create the ML agent instance
    """
    global ml_agent
    if ml_agent is None:
        ml_agent = SideStackerMLAgent()
    return ml_agent

def create_simple_trained_model():
        """
        Create a simple trained model with basic patterns
        This gives you a working model immediately
        """
        agent = SideStackerMLAgent()
        
        # Simple training data for basic patterns
        training_patterns = [
            # Winning patterns (high reward)
            {
                'board': [[1,1,1,None,None,None,None] for _ in range(7)],
                'move': (0, 'R'),
                'reward': 1.0
            },
            # Blocking patterns (medium reward)
            {
                'board': [[2,2,2,None,None,None,None] for _ in range(7)],
                'move': (0, 'R'),
                'reward': 0.8
            },
            # Center play patterns (low reward)
            {
                'board': [[None for _ in range(7)] for _ in range(7)],
                'move': (3, 'L'),
                'reward': 0.3
            }
        ]
        
        # Train with patterns
        for _ in range(1000):  # Simple training loop
            pattern = random.choice(training_patterns)
            available_moves = [(i, side) for i in range(7) for side in ['L', 'R']]
            
            agent.add_training_data(
                pattern['board'], 
                available_moves, 
                pattern['move'], 
                pattern['reward']
            )
            
            if len(agent.memory) >= 32:
                agent.train_step()
        
        # Save the trained model
        agent.save_model()
        logger.info("Simple trained model created and saved")
        return agent


def train_ml_model_background():
    """
    Background training function - can be called periodically
    """
    agent = get_ml_agent()
    
    # Perform training steps if we have enough data
    if len(agent.memory) >= 100:
        total_loss = 0
        training_steps = 10
        
        for _ in range(training_steps):
            loss = agent.train_step()
            if loss:
                total_loss += loss
        
        avg_loss = total_loss / training_steps
        logger.info(f"Training completed. Average loss: {avg_loss:.4f}")
        
        # Save model periodically
        if agent.training_games % 10 == 0:
            agent.save_model()

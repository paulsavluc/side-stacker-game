from django.db import models
import json
import logging
import random

logger = logging.getLogger(__name__)


class Game(models.Model):
    GAME_STATUS_CHOICES = [
        ('waiting', 'Waiting for Player'),
        ('active', 'Active'),
        ('finished', 'Finished'),
    ]
    
    GAME_MODE_CHOICES = [
        ('pvp', 'Player vs Player'),
        ('pva', 'Player vs AI'),
    ]

    DIFFICULTY_LEVELS = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    
    id = models.AutoField(primary_key=True)
    player1_name = models.CharField(max_length=100, default='Player 1')
    player2_name = models.CharField(max_length=100, default='Player 2')
    current_player = models.IntegerField(default=1)  # 1 or 2
    status = models.CharField(max_length=20, choices=GAME_STATUS_CHOICES, default='waiting')
    difficulty = models.CharField(max_length=6, choices=DIFFICULTY_LEVELS, default='easy')
    mode = models.CharField(max_length=10, choices=GAME_MODE_CHOICES, default='pvp')
    winner = models.IntegerField(null=True, blank=True)
    board_state = models.TextField(default='[]')  # JSON string
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    board_state = models.TextField(default='')

    def save(self, *args, **kwargs):
        # Initialize board_state if it's empty when creating a new game
        if not self.board_state:
            empty_board = [[None for _ in range(7)] for _ in range(7)]
            self.board_state = json.dumps(empty_board)
        super().save(*args, **kwargs)

    def get_difficulty_display_name(self):
        """Get human-rea`dable difficulty name"""
        difficulty_map = {
            'easy': 'Easy',
            'medium': 'Medium', 
            'hard': 'Hard'
        }
        return difficulty_map.get(self.difficulty, 'Easy')
    
    def get_board(self):
        if self.board_state:
            try:
                board = json.loads(self.board_state)
                # Ensure it's a 7x7 board
                if len(board) == 7 and all(len(row) == 7 for row in board):
                    return board
            except (json.JSONDecodeError, TypeError):
                empty_board = [[None for _ in range(7)] for _ in range(7)]
                self.set_board(empty_board)
                self.save()
                return empty_board
        
        # Create and save empty board if none exists or is invalid
        empty_board = [[None for _ in range(7)] for _ in range(7)]
        self.set_board(empty_board)
        self.save()
        return empty_board
    
    def set_board(self, board):
        self.board_state = json.dumps(board)
    
    def make_move(self, row, side, player):
        board = self.get_board()

        if not board or len(board) != 7:
            print("Invalid board, reinitializing...")
            board = [[None for _ in range(7)] for _ in range(7)]
            self.set_board(board)
            self.save()
        
        # Find the target column based on side and stacking logic
        target_col = None
        
        if side == 'L':
            # Find leftmost empty position
            for col in range(7):
                if board[row][col] is None:
                    target_col = col
                    break
        elif side == 'R':
            # Find rightmost empty position
            for col in range(6, -1, -1):
                if board[row][col] is None:
                    target_col = col
                    break
        else:
            return False
        
        # Check if move is valid (found an empty position)
        if target_col is None:
            return False  # Row is full
        # Make the move
        board[row][target_col] = player
        
        # Save the updated board
        self.set_board(board)
        
        self.current_player = 2 if player == 1 else 1
        
        game_ended = False
        # Check for winner
        if self.check_winner(board):
            self.winner = player
            self.status = 'finished'
            game_ended = True
        elif self.is_board_full(board):
            self.status = 'finished'
            self.winner = None  # Draw
            game_ended = True
        
        self.save()

        if game_ended:
            self.update_ml_training_data(self.winner)

        return True
    
    def check_winner(self, board):
        # Check horizontal, vertical, and diagonal connections
        for row in range(7):
            for col in range(7):
                if board[row][col] is not None:
                    if (self.check_direction(board, row, col, 1, 0) or  # Horizontal
                        self.check_direction(board, row, col, 0, 1) or  # Vertical
                        self.check_direction(board, row, col, 1, 1) or  # Diagonal \
                        self.check_direction(board, row, col, 1, -1)):  # Diagonal /
                        return True
        return False
    
    def check_direction(self, board, row, col, dr, dc):
        player = board[row][col]
        count = 1
        
        # Check positive direction
        r, c = row + dr, col + dc
        while 0 <= r < 7 and 0 <= c < 7 and board[r][c] == player:
            count += 1
            r, c = r + dr, c + dc
        
        # Check negative direction
        r, c = row - dr, col - dc
        while 0 <= r < 7 and 0 <= c < 7 and board[r][c] == player:
            count += 1
            r, c = r - dr, c - dc
        
        return count >= 4
    
    def is_board_full(self, board):
        for row in board:
            for cell in row:
                if cell is None:
                    return False
        return True
    
    def get_available_moves(self):
        board = self.get_board()
        moves = []
        
        for row in range(7):
            row_data = board[row]
            
            # Find leftmost available position
            for col in range(7):
                if row_data[col] is None:
                    moves.append((row, 'L'))
                    break
            
            # Find rightmost available position
            for col in range(6, -1, -1):
                if row_data[col] is None:
                    moves.append((row, 'R'))
                    break
        
        return moves

    def get_medium_ai_move(self, available_moves):
        board = self.get_board()
        
        # Check for winning moves first
        for row, side in available_moves:
            # Simulate the move
            temp_board = [row[:] for row in board]
            target_col = self.simulate_move(temp_board, row, side, 2)
            if target_col is not None:
                temp_board[row][target_col] = 2
                if self.check_winner(temp_board):
                    return row, side
        
        # Check for blocking opponent's winning moves
        for row, side in available_moves:
            temp_board = [row[:] for row in board]
            target_col = self.simulate_move(temp_board, row, side, 1)
            if target_col is not None:
                temp_board[row][target_col] = 1
                if self.check_winner(temp_board):
                    return row, side
        
        # Otherwise random move
        return random.choice(available_moves)

    def simulate_move(self, board, row, side, player):
        if side == 'L':
            for col in range(7):
                if board[row][col] is None:
                    return col
        elif side == 'R':
            for col in range(6, -1, -1):
                if board[row][col] is None:
                    return col
        return None
    
    def update_ml_training_data(self, winner):
        """
        Update ML training data based on game outcome
        """
        try:
            from .ml_model import get_ml_agent, train_ml_model_background
            import torch
        
            if self.mode == 'pva' and self.difficulty == 'hard':
                ml_agent = get_ml_agent()
                
                # Update rewards based on game outcome
                reward = 0.0
                if winner == 2:  # AI won
                    reward = 1.0
                elif winner == 1:  # AI lost
                    reward = -0.5
                else:  # Draw
                    reward = 0.2

                 # Add current board state as training data
                board = self.get_board()
                available_moves = self.get_available_moves()
                
                if available_moves:
                    # Add training data for the final board state
                    ml_agent.add_training_data(board, available_moves, available_moves[0], reward)
                    
                    # Train the model
                    if len(ml_agent.memory) >= 32:
                        ml_agent.train_step()
                        ml_agent.save_model()
            
                logger.info(f"ML training updated. Winner: {winner}, Reward: {reward}")
            
        except Exception as e:
            logger.error(f"Error updating ML training data: {e}")
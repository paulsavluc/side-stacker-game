import random
import json
import openai
import os
from django.conf import settings
from .models import Game
import logging
from .ml_model import get_ml_agent, create_simple_trained_model

logger = logging.getLogger(__name__)

# Configure OpenAI
openai.api_key = settings.OPENAI_API_KEY


def make_ai_move(game):
    """
    Route to appropriate AI difficulty
    """
    if game.difficulty == 'easy':
        return make_easy_ai_move(game)
    elif game.difficulty == 'medium':
        return make_medium_ai_move(game)
    elif game.difficulty == 'hard':
        return make_hard_ai_move(game)  # Placeholder for future implementation
    else:
        return make_easy_ai_move(game)  # Default to easy
def make_easy_ai_move(game):
    """
    Easy AI: Makes semi-random moves with basic rules
    """
    board = game.get_board()
    available_moves = game.get_available_moves()
    
    if not available_moves:
        return None
    
    # 1. Check if AI can win
    winning_move = find_winning_move(board, 2)
    if winning_move:
        return winning_move
    
    # 2. Check if need to block opponent
    blocking_move = find_winning_move(board, 1)
    if blocking_move:
        return blocking_move
    
    # 3. Make a random move
    return random.choice(available_moves)

def make_medium_ai_move(game):
    """
    Medium AI: Uses OpenAI GPT for strategic decision making
    Combines basic game analysis with AI reasoning
    """
    board = game.get_board()
    available_moves = game.get_available_moves()
    
    if not available_moves:
        return None
    
    # 1. Check if AI can win (highest priority - don't need AI for this)
    winning_move = find_winning_move(board, 2)
    if winning_move:
        logger.info("AI found winning move")
        return winning_move
    
    # 2. Check if need to block opponent (second priority)
    blocking_move = find_winning_move(board, 1)
    if blocking_move:
        logger.info("AI found blocking move")
        return blocking_move
    
    # 3. Use OpenAI for strategic decision making
    try:
        ai_move = get_openai_strategic_move(board, available_moves)
        if ai_move and ai_move in available_moves:
            logger.info(f"AI chose strategic move via OpenAI: {ai_move}")
            return ai_move
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
    
    # 4. Fallback to basic strategy if OpenAI fails
    logger.info("Falling back to basic strategy")
    return get_fallback_strategic_move(board, available_moves)

def make_hard_ai_move(game):
    """
    Hard AI: Uses ML model - now with complete training
    """
    board = game.get_board()
    available_moves = game.get_available_moves()
    
    if not available_moves:
        return None
    
    # 1. Check if AI can win (always prioritize winning)
    winning_move = find_winning_move(board, 2)
    if winning_move:
        logger.info("AI found winning move")
        return winning_move
    
    # 2. Check if need to block opponent
    blocking_move = find_winning_move(board, 1)
    if blocking_move:
        logger.info("AI found blocking move")
        return blocking_move
    
    # 3. Use ML model - create if doesn't exist
    try:
        ml_agent = get_ml_agent()
        
        # Check if model is trained, if not create simple trained model
        if not os.path.exists(ml_agent.model_path):
            logger.info("No trained model found, creating simple trained model")
            ml_agent = create_simple_trained_model()  # NOW WE ACTUALLY USE IT!
        
        ai_move = ml_agent.predict_move(board, available_moves, use_exploration=True)
        
        if ai_move and ai_move in available_moves:
            logger.info(f"AI chose ML-based move: {ai_move}")
            return ai_move
            
    except Exception as e:
        logger.error(f"ML model error: {e}")
    
    # 4. Fallback to strategic move
    logger.info("Falling back to strategic move")
    return get_fallback_strategic_move(board, available_moves)

def get_openai_strategic_move(board, available_moves):
    """
    Use OpenAI GPT to analyze the board and suggest the best move
    """
    # Convert board to a readable format
    board_str = format_board_for_ai(board)
    moves_str = format_moves_for_ai(available_moves)
    
    prompt = f"""
You are playing a Side-Stacker game (like Connect 4, but pieces stack from sides).
Board is 7x7. Players take turns adding pieces to rows from left (L) or right (R) side.
Goal: Get 4 consecutive pieces in any direction (horizontal, vertical, diagonal).

Current board state (X=Player1, O=AI/You, _=empty):
{board_str}

Available moves: {moves_str}
Format: (row, side) where row is 0-6, side is L or R

You are O (Player 2). Analyze the position and choose the BEST strategic move.

Consider:
1. Creating multiple threats
2. Controlling center positions
3. Setting up future winning combinations
4. Preventing opponent threats
5. Building connected pieces

Respond with ONLY the move in format: (row, side)
Example: (3, L) or (1, R)
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert Side-Stacker game player. Analyze positions strategically and suggest optimal moves."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=5,
            temperature=0.3  # Lower temperature for more consistent strategic play
        )
        
        move_text = response.choices[0].message.content.strip()
        logger.info(f"OpenAI response: {move_text}")
        
        # Parse the response
        move = parse_ai_response(move_text)
        return move
        
    except openai.error.OpenAIError as e:
        logger.error(f"OpenAI API call failed: {e}")
        if "insufficient_quota" in str(e):
            logger.warning("OpenAI quota exceeded, using fallback strategy")
        return get_fallback_strategic_move(board, available_moves)

def format_board_for_ai(board):
    """
    Format the board in a readable way for the AI
    """
    formatted = ""
    for i, row in enumerate(board):
        row_str = ""
        for cell in row:
            if cell == 1:
                row_str += "X "
            elif cell == 2:
                row_str += "O "
            else:
                row_str += "_ "
        formatted += f"Row {i}: {row_str}\n"
    return formatted

def format_moves_for_ai(available_moves):
    """
    Format available moves for the AI
    """
    return ", ".join([f"({row}, {side})" for row, side in available_moves])

def parse_ai_response(response_text):
    """
    Parse OpenAI response to extract the move
    """
    import re
    
    # Look for pattern like (3, L) or (1, R)
    pattern = r'\((\d+),\s*([LR])\)'
    match = re.search(pattern, response_text)
    
    if match:
        row = int(match.group(1))
        side = match.group(2)
        
        # Validate the move
        if 0 <= row <= 6 and side in ['L', 'R']:
            return (row, side)
    
    logger.warning(f"Could not parse AI response: {response_text}")
    return None

def get_fallback_strategic_move(board, available_moves):
    """
    Fallback strategy when OpenAI is not available
    Uses basic strategic principles
    """
    move_scores = []
    
    for move in available_moves:
        row, side = move
        score = evaluate_move_strategically(board, row, side)
        move_scores.append((move, score))
    
    # Sort by score and add some randomness
    move_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Pick from top 3 moves with weighted randomness
    top_moves = move_scores[:min(3, len(move_scores))]
    weights = [3, 2, 1][:len(top_moves)]
    
    return random.choices([move for move, _ in top_moves], weights=weights)[0]

def evaluate_move_strategically(board, row, side):
    """
    Basic strategic evaluation for fallback
    """
    score = 0
    
    # Center rows are better
    center_bonus = 7 - abs(row - 3)
    score += center_bonus * 3
    
    # Simulate the move
    test_board = simulate_move(board, row, side, 2)
    if not test_board:
        return -1000
    
    # Count connections
    target_col = get_target_column(board, row, side)
    if target_col is not None:
        score += count_connections(test_board, row, target_col, 2) * 5
        
        # Penalty if it helps opponent
        score -= count_connections(test_board, row, target_col, 1) * 2
    
    return score

def count_connections(board, row, col, player):
    """
    Count existing connections from this position
    """
    directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
    total = 0
    
    for dr, dc in directions:
        count = 1  # Current piece
        
        # Count in positive direction
        r, c = row + dr, col + dc
        while 0 <= r < 7 and 0 <= c < 7 and board[r][c] == player:
            count += 1
            r, c = r + dr, c + dc
        
        # Count in negative direction
        r, c = row - dr, col - dc
        while 0 <= r < 7 and 0 <= c < 7 and board[r][c] == player:
            count += 1
            r, c = r - dr, c - dc
        
        if count >= 2:  # At least 2 in a row
            total += count
    
    return total

def get_target_column(board, row, side):
    """
    Get the column where the piece would be placed
    """
    if side == 'L':
        for col in range(7):
            if board[row][col] is None:
                return col
    elif side == 'R':
        for col in range(6, -1, -1):
            if board[row][col] is None:
                return col
    return None

def find_winning_move(board, player):
    """
    Find a move that creates 4 in a row for the given player
    Returns (row, side) tuple or None
    """
    # Try each possible move
    for row in range(7):
        for side in ['L', 'R']:
            # Simulate the move
            test_board = simulate_move(board, row, side, player)
            if test_board and check_winner_for_board(test_board, player):
                return (row, side)
    
    return None

def simulate_move(board, row, side, player):
    """
    Simulate a move without modifying the original board
    Returns new board state or None if move is invalid
    """
    # Create a copy of the board
    test_board = [row[:] for row in board]
    
    # Find the target column based on side
    target_col = None
    
    if side == 'L':
        # Find leftmost empty position
        for col in range(7):
            if test_board[row][col] is None:
                target_col = col
                break
    elif side == 'R':
        # Find rightmost empty position
        for col in range(6, -1, -1):
            if test_board[row][col] is None:
                target_col = col
                break
    
    # Check if move is valid
    if target_col is None:
        return None  # Row is full
    
    # Make the move on test board
    test_board[row][target_col] = player
    return test_board

def check_winner_for_board(board, player):
    """
    Check if the given player has won on the board
    """
    for row in range(7):
        for col in range(7):
            if board[row][col] == player:
                if (check_direction_for_board(board, row, col, 1, 0, player) or  # Horizontal
                    check_direction_for_board(board, row, col, 0, 1, player) or  # Vertical
                    check_direction_for_board(board, row, col, 1, 1, player) or  # Diagonal \
                    check_direction_for_board(board, row, col, 1, -1, player)):  # Diagonal /
                    return True
    return False

def check_direction_for_board(board, row, col, dr, dc, player):
    """
    Check if there are 4 consecutive pieces in a direction
    """
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
def handle_openai_error(e):
    """
    Handle different types of OpenAI API errors
    """
    if hasattr(e, 'code'):
        if e.code == 'rate_limit_exceeded':
            logger.warning("OpenAI rate limit exceeded, using fallback strategy")
        elif e.code == 'insufficient_quota':
            logger.warning("OpenAI quota exceeded, using fallback strategy")
        else:
            logger.error(f"OpenAI API error: {e}")
    else:
        logger.error(f"Unexpected error with OpenAI: {e}")

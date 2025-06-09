from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from game.models import Game
import random
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
def create_game(request):
    mode = request.data.get('mode', 'pvp')
    difficulty = request.data.get('difficulty', 'easy')
    player1_name = request.data.get('player1_name', 'Player 1')
    player2_name = request.data.get('player2_name', 'Player 2')
    
    game = Game.objects.create(
        mode=mode,
        difficulty=difficulty,
        player1_name=player1_name,
        player2_name=player2_name,
        status='active' if mode == 'pva' else 'waiting'
    )

    # Ensure board is properly initialized
    board = game.get_board()
    game.set_board(board)
    game.save()
    
    return Response({
        'game_id': game.id,
        'board': board,
        'current_player': game.current_player,
        'status': game.status,
        'mode': game.mode,
        'difficulty': game.difficulty,
        'player1_name': game.player1_name,
        'player2_name': game.player2_name,
    })

@api_view(['GET'])
def get_game(request, game_id):
    try:
        game = Game.objects.get(id=game_id)
        return Response({
            'id': game.id,
            'board': game.get_board(),
            'current_player': game.current_player,
            'status': game.status,
            'winner': game.winner,
            'mode': game.mode,
            'difficulty': game.difficulty,
            'player1_name': game.player1_name,
            'player2_name': game.player2_name,
        })
    except Game.DoesNotExist:
        return Response({'error': 'Game not found'}, status=404)

@api_view(['POST'])
def join_game(request, game_id):
    try:
        game = Game.objects.get(id=game_id)
        if game.status == 'waiting':
            game.status = 'active'
            game.player2_name = request.data.get('player_name', 'Player 2')
            game.save()
            
            return Response({
                'success': True,
                'game_data': {
                    'id': game.id,
                    'board': game.get_board(),
                    'current_player': game.current_player,
                    'status': game.status,
                    'player1_name': game.player1_name,
                    'player2_name': game.player2_name,
                }
            })
        else:
            return Response({'error': 'Game is not available'}, status=400)
    except Game.DoesNotExist:
        return Response({'error': 'Game not found'}, status=404)

@api_view(['POST'])
def ai_move(request, game_id):
    try:
        game = Game.objects.get(id=game_id)
        if game.mode == 'pva' and game.current_player == 2:
            # Simple AI: random move
            available_moves = game.get_available_moves()
            if available_moves:
                if game.difficulty == 'easy':
                    row, side = random.choice(available_moves)
                elif game.difficulty == 'medium':
                    row, side = game.get_medium_ai_move(available_moves)
                else:  # hard
                    row, side = game.get_hard_ai_move(game, available_moves)  # Implement later

                success = game.make_move(row, side, 2)

                if success:
                    return Response({
                        'success': True,
                        'move': {'row': row, 'side': side},
                        'game_data': {
                            'id': game.id,
                            'board': game.get_board(),
                            'current_player': game.current_player,
                            'status': game.status,
                            'winner': game.winner,
                        }
                    })
                else:
                    return Response({'error': 'Invalid move'}, status=400)
        return Response({'error': 'Invalid AI move request'}, status=400)
    except Game.DoesNotExist:
        return Response({'error': 'Game not found'}, status=404)
    except Exception as e:
        logger.error(f"AI move error: {e}")
        return Response({'error': 'Internal server error'}, status=500)
    
def get_hard_ai_move(game, available_moves):
    """
    Get AI move for hard difficulty using ML model
    """
    try:
        from game.ml_model import get_ml_agent
        from game.ai_bot import make_hard_ai_move
        
        # Use the ML-based AI move
        move = make_hard_ai_move(game)
        if move and move in available_moves:
            return move
        else:
            # Fallback to random if ML fails
            logger.warning("ML model failed, using random move")
            return random.choice(available_moves)
            
    except ImportError:
        logger.warning("ML model not available, using random move")
        return random.choice(available_moves)
    except Exception as e:
        logger.error(f"Hard AI error: {e}")
        return random.choice(available_moves)
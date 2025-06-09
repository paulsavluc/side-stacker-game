# Enhanced WebSocket consumer with better player management and reconnection handling
import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Game
import logging

logger = logging.getLogger(__name__)

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.game_group_name = f'game_{self.game_id}'
        self.player_id = None
        self.player_number = None

        logger.info(f"WebSocket connecting - Game ID: {self.game_id}")

        await self.channel_layer.group_add(
            self.game_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.game_group_name,
            self.channel_name
        )
        logger.info(f"WebSocket disconnected - Game ID: {self.game_id}, Player: {self.player_id}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            logger.info(f"Received data: {data}")
            action = data['action']

            if action == 'make_move':
                row = data['row']
                side = data['side']
                player = data['player']
                player_id = data.get('player_id')
                
                # Verify player can make this move
                if await self.can_player_move(self.game_id, player, player_id):
                    success = await self.make_move(self.game_id, row, side, player)
                    
                    if success:
                        game_data = await self.get_game_data(self.game_id)
                        await self.channel_layer.group_send(
                            self.game_group_name,
                            {
                                'type': 'game_update',
                                'game_data': game_data
                            }
                        )
                        
                        # Trigger AI move if needed
                        if game_data['mode'] == 'pva' and game_data['current_player'] == 2 and game_data['status'] == 'active':
                            # Add a small delay to make AI feel more natural
                            await asyncio.sleep(2)  # 2 second delay
                            ai_success = await self.trigger_ai_move(self.game_id)
                            
                            if ai_success:
                                # Send updated game state after AI move
                                updated_game_data = await self.get_game_data(self.game_id)
                                await self.channel_layer.group_send(
                                    self.game_group_name,
                                    {
                                        'type': 'game_update',
                                        'game_data': updated_game_data
                                    }
                                )
            
            elif action == 'creator_join':
                # Handle game creator connecting (they should be player 1)
                player_name = data.get('player_name', 'Player 1')
                player_id = data.get('player_id')
                self.player_id = player_id
                
                player_number = await self.assign_player_one(self.game_id, player_name, player_id)
                
                if player_number:
                    self.player_number = player_number
                    
                    # Send player assignment to this specific client
                    await self.send(text_data=json.dumps({
                        'type': 'player_assignment',
                        'player_number': player_number
                    }))
                    
                    # Send current game state
                    game_data = await self.get_game_data(self.game_id)
                    await self.send(text_data=json.dumps({
                        'type': 'game_update',
                        'game_data': game_data
                    }))
                            
            elif action == 'join_game':
                player_name = data.get('player_name', 'Player 2')
                player_id = data.get('player_id')
                self.player_id = player_id

                logger.info(f"===Player {player_name} joining game {self.game_id} with ID {player_id}")
                
                player_number = await self.join_game(self.game_id, player_name, player_id)
                if player_number:
                    self.player_number = player_number
                    
                    # Send player assignment to this specific client
                    await self.send(text_data=json.dumps({
                        'type': 'player_assignment',
                        'player_number': player_number
                    }))
                    
                    # Broadcast game update to all clients
                    game_data = await self.get_game_data(self.game_id)
                    await self.channel_layer.group_send(
                        self.game_group_name,
                        {
                            'type': 'player_joined',
                            'game_data': game_data
                        }
                    )
                    
            elif action == 'rejoin_game':
                player_id = data.get('player_id')
                player_name = data.get('player_name')
                self.player_id = player_id
                
                # Get current game state and send to rejoining player
                game_data = await self.get_game_data(self.game_id)
                player_number = None

                if game_data:
                    if game_data['player1_name'] == player_name:
                        player_number = 1
                    elif game_data['player2_name'] == player_name:
                        player_number = 2
                
                if player_number:
                    self.player_number = player_number
                    await self.send(text_data=json.dumps({
                        'type': 'player_assignment',
                        'player_number': player_number
                    }))
                
                await self.send(text_data=json.dumps({
                    'type': 'game_update',
                    'game_data': game_data
                }))

        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'An error occurred processing your request'
            }))

    async def player_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'player_joined',
            'game_data': event['game_data']
        }))

    async def game_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'game_update',
            'game_data': event['game_data']
        }))

    @database_sync_to_async
    def can_player_move(self, game_id, player, player_id):
        """Verify if the player can make a move"""
        try:
            game = Game.objects.get(id=game_id)
            return (game.status == 'active' and 
                   game.current_player == player and
                   self.verify_player_identity(game, player, player_id))
        except Game.DoesNotExist:
            return False

    @database_sync_to_async
    def verify_player_identity(self, game, player, player_id):
        """Verify player identity - you can enhance this with session management"""
        # For now, basic verification - you can enhance with database session tracking
        return True

    @database_sync_to_async
    def make_move(self, game_id, row, side, player):
        try:
            game = Game.objects.get(id=game_id)
            return game.make_move(row, side, player)
        except Game.DoesNotExist:
            return False

    @database_sync_to_async
    def get_game_data(self, game_id):
        try:
            game = Game.objects.get(id=game_id)
            return {
                'id': game.id,
                'board': game.get_board(),
                'current_player': game.current_player,
                'status': game.status,
                'winner': game.winner,
                'player1_name': game.player1_name,
                'player2_name': game.player2_name,
                'mode': game.mode,
            }
        except Game.DoesNotExist:
            return None
        
    @database_sync_to_async
    def assign_player_one(self, game_id, player_name, player_id):
        """Assign player 1 when they create or reconnect to a game"""
        try:
            game = Game.objects.get(id=game_id)
            
            # Only assign player 1 if the game is waiting and player1_name is not set
            if game.status == 'waiting' and not game.player1_name:
                game.player1_name = player_name
                game.save()
                return 1
            # If player1_name matches, this is a reconnection
            elif game.player1_name == player_name:
                return 1
            # Don't assign if player1 slot is already taken by someone else
            return None
            
        except Game.DoesNotExist:
            return None

    @database_sync_to_async
    def join_game(self, game_id, player_name, player_id):
        """Enhanced join game with player tracking"""
        try:
            game = Game.objects.get(id=game_id)
            logger.info(f"Attempting to join as player 2 - Game found - ID: {game.id}, Status: {game.status}, Player1: {game.player1_name}, Player2: {game.player2_name}, PlayerName: {player_name}")
            
            if (game.status == 'waiting' and 
                game.player1_name and 
                game.player1_name != player_name):
                
                game.player2_name = player_name
                game.status = 'active'
                game.save()
                logger.info(f"Player 2 joined: {player_name}")
                return 2
                
            # Handle reconnection for existing player 2
            elif game.player2_name == player_name:
                return 2
                
            # For PvA mode, don't allow joining as player 2
            elif game.mode == 'pva':
                return None
                    
        except Game.DoesNotExist:
            logger.error(f"Game with ID {game_id} does not exist")
            
        return None

    @database_sync_to_async
    def get_player_number(self, game_id, player_id):
        """Get player number for reconnection"""
        # You can enhance this with proper session tracking
        # For now, return None to let client rejoin normally
        return None

    @database_sync_to_async
    def trigger_ai_move(self, game_id):
        """Trigger AI move for PvA mode"""
        try:
            from .ai_bot import make_ai_move  # Import your AI logic
            game = Game.objects.get(id=game_id)

            if game.current_player == 2 and game.status == 'active':
                logger.info(f"Triggering AI move for game {game_id}, difficulty: {game.difficulty}")
                ai_move = make_ai_move(game)
                if ai_move:
                    row, side = ai_move
                    success = game.make_move(row, side, 2)  # AI is player 2
                    logger.info(f"AI made move: ({row}, {side}), success: {success}")
                    return success
        except Exception as e:
            logger.error(f"AI move failed: {e}")
        return False

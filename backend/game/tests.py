from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from game.models import Game
from game.ai_bot import make_easy_ai_move, find_winning_move

class GameModelTest(TestCase):
    def setUp(self):
        self.game = Game.objects.create(
            mode='pvp',
            player1_name='Alice',
            player2_name='Bob'
        )

    def test_game_creation(self):
        """Test basic game creation"""
        self.assertEqual(self.game.current_player, 1)
        self.assertEqual(len(self.game.get_board()), 7)

    def test_make_move(self):
        """Test making a move"""
        success = self.game.make_move(0, 'L', 1)
        self.assertTrue(success)
        
        board = self.game.get_board()
        self.assertEqual(board[0][0], 1)
        self.assertEqual(self.game.current_player, 2)

    def test_horizontal_win(self):
        """Test horizontal win detection"""
        # Make 4 moves in a row
        self.game.make_move(0, 'L', 1)  # [1, _, _, _, _, _, _]
        self.game.make_move(1, 'L', 2)  # Opponent move
        self.game.make_move(0, 'L', 1)  # [1, 1, _, _, _, _, _]
        self.game.make_move(1, 'L', 2)  # Opponent move
        self.game.make_move(0, 'L', 1)  # [1, 1, 1, _, _, _, _]
        self.game.make_move(1, 'L', 2)  # Opponent move
        self.game.make_move(0, 'L', 1)  # [1, 1, 1, 1, _, _, _] - WIN!
        
        self.assertEqual(self.game.winner, 1)
        self.assertEqual(self.game.status, 'finished')

    def test_full_row_rejection(self):
        """Test that moves are rejected when row is full"""
        # Fill entire row
        for i in range(7):
            self.game.make_move(0, 'L', 1)
        
        # Try to make another move - should fail
        success = self.game.make_move(0, 'L', 1)
        self.assertFalse(success)

class AIBotTest(TestCase):
    def setUp(self):
        self.game = Game.objects.create(
            mode='pva',
            difficulty='easy'
        )

    def test_ai_makes_valid_move(self):
        """Test that AI makes a valid move"""
        move = make_easy_ai_move(self.game)
        self.assertIsNotNone(move)
        
        row, side = move
        self.assertIn(row, range(7))
        self.assertIn(side, ['L', 'R'])

    def test_ai_takes_winning_move(self):
        """Test AI takes winning move when available"""
        # Set up a winning scenario for AI (player 2)
        board = self.game.get_board()
        board[0] = [2, 2, 2, None, None, None, None]
        self.game.set_board(board)
        
        move = make_easy_ai_move(self.game)
        self.assertEqual(move, (0, 'L'))

class GameAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_create_game(self):
        """Test creating a game via API"""
        data = {
            'mode': 'pvp',
            'player1_name': 'Alice'
        }
        
        response = self.client.post('/api/games/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['mode'], 'pvp')
        self.assertEqual(response.data['player1_name'], 'Alice')

    def test_get_game(self):
        """Test retrieving game data"""
        game = Game.objects.create(mode='pvp', player1_name='Alice')
        
        response = self.client.get(f'/api/games/{game.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['player1_name'], 'Alice')

    def test_ai_move(self):
        """Test AI move endpoint"""
        game = Game.objects.create(
            mode='pva',
            difficulty='easy',
            status='active',
            current_player=2
        )
        
        response = self.client.post(f'/api/games/{game.id}/ai-move/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

# Run tests with: python manage.py test
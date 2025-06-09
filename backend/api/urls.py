from django.urls import path
from . import views

urlpatterns = [
    path('games/', views.create_game, name='create_game'),
    path('games/<int:game_id>/', views.get_game, name='get_game'),
    # path('games/<int:game_id>/join/', views.join_game, name='join_game'),
    path('games/<int:game_id>/ai-move/', views.ai_move, name='ai_move'),
]

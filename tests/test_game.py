"""
Unit tests for the core (CV-free) game logic. These run in milliseconds
with no camera, no MediaPipe, and no display -- just the state machine.

Run with:  pytest
"""

import math

import pytest

from src.game import SnakeGame, GameStatus


def make_game(**kwargs):
    defaults = dict(width=400, height=300)
    defaults.update(kwargs)
    return SnakeGame(**defaults)


def test_starts_waiting_for_hand():
    game = make_game()
    assert game.status == GameStatus.WAITING_FOR_HAND


def test_hand_found_starts_the_game():
    game = make_game()
    state = game.update(target=(200, 150), hand_found=True)
    assert state.status == GameStatus.PLAYING


def test_losing_hand_pauses_not_game_over():
    game = make_game()
    game.update(target=(200, 150), hand_found=True)
    state = game.update(target=None, hand_found=False)
    assert state.status == GameStatus.PAUSED


def test_head_moves_toward_target():
    game = make_game(base_speed=10)
    game.update(target=(200, 150), hand_found=True)  # spawn at center-ish
    start = tuple(game.head)
    state = game.update(target=(400, 150), hand_found=True)
    assert state.head[0] > start[0]  # moved right, toward the target


def test_head_never_leaves_bounds():
    game = make_game(base_speed=50)
    for _ in range(50):
        state = game.update(target=(-1000, -1000), hand_found=True)
    assert 0 <= state.head[0] <= game.width
    assert 0 <= state.head[1] <= game.height


def test_eating_food_increases_score_and_length():
    game = make_game()
    game.update(target=(200, 150), hand_found=True)
    initial_length = game.length
    # Walk straight toward the food every frame until it's eaten.
    state = None
    for _ in range(500):
        fx, fy = game.food
        state = game.update(target=(fx, fy), hand_found=True)
        if state.score > 0:
            break
    assert state.score >= 1
    assert game.length > initial_length


def test_boost_moves_faster_than_base_speed():
    slow = make_game(base_speed=5, boost_speed=20)
    slow.update(target=(0, 0), hand_found=True)  # let it spawn/settle
    slow_start = tuple(slow.head)
    slow.update(target=(399, 0), hand_found=True, boosting=False)
    slow_dist = math.hypot(slow.head[0] - slow_start[0], slow.head[1] - slow_start[1])

    fast = make_game(base_speed=5, boost_speed=20)
    fast.update(target=(0, 0), hand_found=True)
    fast_start = tuple(fast.head)
    fast.update(target=(399, 0), hand_found=True, boosting=True)
    fast_dist = math.hypot(fast.head[0] - fast_start[0], fast.head[1] - fast_start[1])

    assert fast_dist > slow_dist


def test_reset_preserves_high_score():
    game = make_game()
    game.high_score = 7
    game.reset()
    assert game.high_score == 7
    assert game.score == 0
    assert game.status == GameStatus.WAITING_FOR_HAND


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

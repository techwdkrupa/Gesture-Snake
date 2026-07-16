"""
game.py
-------
A "free movement" Snake variant built for gesture control.

Instead of a grid-locked snake that turns on key presses, the head smoothly
chases wherever your index fingertip is. The body is a trail of past head
positions, evenly spaced. This feels natural with a webcam since hand
tracking is analog and a little noisy -- grid snapping would feel jittery.

The class knows nothing about OpenCV/MediaPipe; it just takes an (x, y)
target position each frame and returns a state you can render however you
like. That keeps it easy to unit test and easy to reuse (e.g. a mouse-driven
version for testing without a webcam).
"""

import math
import random
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Tuple


class GameStatus(Enum):
    WAITING_FOR_HAND = auto()   # no hand detected yet
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()


@dataclass
class GameState:
    status: GameStatus
    head: Tuple[float, float]
    segments: List[Tuple[float, float]]
    food: Tuple[int, int]
    score: int
    high_score: int
    boosting: bool = False


class SnakeGame:
    def __init__(
        self,
        width: int,
        height: int,
        segment_spacing: int = 14,
        base_speed: float = 14.0,
        boost_speed: float = 26.0,
        collision_radius: int = 10,
        food_radius: int = 14,
        starting_length: int = 6,
    ):
        self.width = width
        self.height = height
        self.segment_spacing = segment_spacing
        self.base_speed = base_speed
        self.boost_speed = boost_speed
        self.collision_radius = collision_radius
        self.food_radius = food_radius
        self.starting_length = starting_length
        self.high_score = 0
        self.reset()

    def reset(self) -> None:
        cx, cy = self.width / 2, self.height / 2
        self.head = [cx, cy]
        # Path history: a dense list of past head positions we sample the
        # body from. Longer than we need so the snake can grow into it.
        self._path = deque([tuple(self.head)] * 2000, maxlen=4000)
        self.length = self.starting_length
        self.score = 0
        self.status = GameStatus.WAITING_FOR_HAND
        self.food = self._spawn_food()
        self._growth_pending = 0

    # -- main update, called once per frame -----------------------------

    def update(self, target, hand_found: bool, boosting: bool = False) -> GameState:
        if not hand_found:
            if self.status == GameStatus.PLAYING:
                self.status = GameStatus.PAUSED
            elif self.status not in (GameStatus.GAME_OVER,):
                self.status = GameStatus.WAITING_FOR_HAND
        elif self.status in (GameStatus.WAITING_FOR_HAND, GameStatus.PAUSED):
            self.status = GameStatus.PLAYING

        if self.status == GameStatus.PLAYING and target is not None:
            self._move_toward(target, boosting)
            self._path.appendleft(tuple(self.head))
            self._check_food()
            self._check_self_collision()

        segments = self._build_segments()
        return GameState(
            status=self.status,
            head=tuple(self.head),
            segments=segments,
            food=self.food,
            score=self.score,
            high_score=self.high_score,
            boosting=boosting,
        )

    def pause(self) -> None:
        if self.status == GameStatus.PLAYING:
            self.status = GameStatus.PAUSED

    def resume(self) -> None:
        if self.status == GameStatus.PAUSED:
            self.status = GameStatus.PLAYING

    # -- internals --------------------------------------------------------

    def _move_toward(self, target, boosting: bool) -> None:
        tx, ty = target
        dx, dy = tx - self.head[0], ty - self.head[1]
        dist = math.hypot(dx, dy)
        speed = self.boost_speed if boosting else self.base_speed
        if dist < 1e-3:
            return
        step = min(dist, speed)
        self.head[0] += dx / dist * step
        self.head[1] += dy / dist * step
        self.head[0] = max(0, min(self.width, self.head[0]))
        self.head[1] = max(0, min(self.height, self.head[1]))

    def _build_segments(self) -> List[Tuple[float, float]]:
        """Walk backwards through path history, picking points spaced
        `segment_spacing` apart, until we have `length` segments."""
        segments = [tuple(self.head)]
        last = segments[0]
        for point in self._path:
            if math.hypot(point[0] - last[0], point[1] - last[1]) >= self.segment_spacing:
                segments.append(point)
                last = point
                if len(segments) >= self.length:
                    break
        return segments

    def _check_food(self) -> None:
        fx, fy = self.food
        if math.hypot(self.head[0] - fx, self.head[1] - fy) < self.food_radius:
            self.length += 3
            self.score += 1
            self.high_score = max(self.high_score, self.score)
            self.food = self._spawn_food()

    def _check_self_collision(self) -> None:
        # Skip a "safe" run of segments closest to the head so the snake
        # doesn't instantly collide with itself while turning tightly.
        safe_gap = 6
        segments = self._build_segments()
        for seg in segments[safe_gap:]:
            if math.hypot(self.head[0] - seg[0], self.head[1] - seg[1]) < self.collision_radius:
                self.status = GameStatus.GAME_OVER
                return

    def _spawn_food(self) -> Tuple[int, int]:
        margin = 40
        return (
            random.randint(margin, max(margin, self.width - margin)),
            random.randint(margin, max(margin, self.height - margin)),
        )

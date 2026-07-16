"""
ui.py
-----
All drawing/rendering code lives here so game.py stays pure logic and
main.py stays a thin loop. Everything is drawn with OpenCV primitives --
no extra asset files needed, so the project runs the instant you clone it.
"""

import time
from typing import Tuple

import cv2
import numpy as np

from src.game import GameStatus

# -- palette -----------------------------------------------------------
BG_DIM = 0.45                 # how much to darken the camera feed
NEON_GREEN = (100, 255, 120)
NEON_CYAN = (255, 230, 60)
NEON_PINK = (180, 90, 255)
WHITE = (245, 245, 245)
FOOD_COLOR = (60, 90, 255)
DANGER = (70, 70, 255)


def darken(frame: np.ndarray, amount: float = BG_DIM) -> np.ndarray:
    """Dim the raw camera feed so the neon UI pops on top of it."""
    overlay = np.zeros_like(frame)
    return cv2.addWeighted(frame, 1 - amount, overlay, amount, 0)


def _pt(p) -> Tuple[int, int]:
    return (int(round(p[0])), int(round(p[1])))


def draw_snake(frame: np.ndarray, segments, boosting: bool) -> None:
    if len(segments) < 2:
        return
    pts = [_pt(p) for p in segments]
    n = len(pts)
    for i in range(n - 1):
        # Fade + thin the tail so the snake reads as having depth/motion.
        t = i / max(1, n - 1)
        thickness = max(2, int(14 * (1 - t)))
        color = NEON_CYAN if boosting else NEON_GREEN
        color = tuple(int(c * (1 - 0.5 * t)) for c in color)
        cv2.line(frame, pts[i], pts[i + 1], color, thickness, cv2.LINE_AA)
    # Head: a bright filled circle with a soft ring, like an eye.
    head = pts[0]
    cv2.circle(frame, head, 12, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(frame, head, 12, NEON_GREEN, 2, cv2.LINE_AA)


def draw_food(frame: np.ndarray, food, t: float) -> None:
    food = _pt(food)
    pulse = 6 + int(3 * abs(np.sin(t * 4)))
    cv2.circle(frame, food, 14 + pulse, tuple(int(c * 0.4) for c in FOOD_COLOR), 2, cv2.LINE_AA)
    cv2.circle(frame, food, 14, FOOD_COLOR, -1, cv2.LINE_AA)
    cv2.circle(frame, food, 5, WHITE, -1, cv2.LINE_AA)


def _panel(frame, x, y, w, h, alpha=0.55):
    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), (20, 20, 20), -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


def draw_hud(frame: np.ndarray, score: int, high_score: int, boosting: bool) -> None:
    h, w = frame.shape[:2]
    _panel(frame, 0, 0, w, 64)
    cv2.putText(frame, "GESTURE SNAKE", (18, 42), cv2.FONT_HERSHEY_DUPLEX, 1.0, NEON_GREEN, 2, cv2.LINE_AA)

    score_txt = f"SCORE {score}"
    (tw, _), _ = cv2.getTextSize(score_txt, cv2.FONT_HERSHEY_DUPLEX, 0.9, 2)
    cv2.putText(frame, score_txt, (w - tw - 24, 30), cv2.FONT_HERSHEY_DUPLEX, 0.9, WHITE, 2, cv2.LINE_AA)
    best_txt = f"BEST {high_score}"
    (tw2, _), _ = cv2.getTextSize(best_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
    cv2.putText(frame, best_txt, (w - tw2 - 24, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.6, NEON_CYAN, 1, cv2.LINE_AA)

    if boosting:
        cv2.putText(frame, "BOOST", (18, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, NEON_CYAN, 2, cv2.LINE_AA)

    _panel(frame, 0, h - 34, w, 34, alpha=0.5)
    cv2.putText(
        frame,
        "Point index finger to steer  |  pinch = boost  |  open palm = pause  |  Q = quit  R = restart",
        (14, h - 11),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (210, 210, 210),
        1,
        cv2.LINE_AA,
    )


def draw_center_message(frame: np.ndarray, title: str, subtitle: str = "", color=WHITE) -> None:
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (10, 10, 10), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    (tw, th), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_DUPLEX, 1.4, 3)
    cv2.putText(frame, title, ((w - tw) // 2, h // 2 - 10), cv2.FONT_HERSHEY_DUPLEX, 1.4, color, 3, cv2.LINE_AA)

    if subtitle:
        (sw, sh), _ = cv2.getTextSize(subtitle, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)
        cv2.putText(
            frame, subtitle, ((w - sw) // 2, h // 2 + 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (220, 220, 220), 1, cv2.LINE_AA,
        )


def draw_status_overlay(frame: np.ndarray, status: GameStatus, score: int) -> None:
    if status == GameStatus.WAITING_FOR_HAND:
        draw_center_message(frame, "SHOW YOUR HAND TO START", "Hold your hand up so the camera can see it")
    elif status == GameStatus.PAUSED:
        draw_center_message(frame, "PAUSED", "Hand lost or palm open -- show your index finger to resume", NEON_CYAN)
    elif status == GameStatus.GAME_OVER:
        draw_center_message(frame, "GAME OVER", f"Score: {score}   |   Press R to play again", DANGER)


def draw_fingertip_cursor(frame: np.ndarray, point, pinching: bool) -> None:
    if point is None:
        return
    point = _pt(point)
    color = NEON_PINK if pinching else NEON_CYAN
    radius = 8 if pinching else 6
    cv2.circle(frame, point, radius, color, -1, cv2.LINE_AA)
    cv2.circle(frame, point, radius + 6, color, 1, cv2.LINE_AA)

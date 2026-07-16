"""
Generates assets/demo.gif by driving the real game + rendering code with a
synthetic fingertip path (a looping figure-eight), instead of a live camera
feed. This lets the README show real gameplay footage without requiring a
webcam recording, while still exercising the actual SnakeGame and ui module
(no separate "demo-only" rendering path to keep in sync).
"""

import math
import os
import sys

import cv2
import imageio.v2 as imageio
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game import SnakeGame
from src import ui

WIDTH, HEIGHT = 480, 320
FRAMES = 140
OUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "demo.gif")


def synthetic_background(t: float) -> np.ndarray:
    """A soft dark gradient, standing in for a dimmed webcam frame."""
    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    top = np.array([28, 22, 18])
    bottom = np.array([8, 8, 10])
    for y in range(HEIGHT):
        a = y / HEIGHT
        frame[y, :] = (top * (1 - a) + bottom * a).astype(np.uint8)
    return frame


def fingertip_path(t: float):
    cx, cy = WIDTH / 2, HEIGHT / 2
    x = cx + math.sin(t * 1.3) * (WIDTH * 0.32)
    y = cy + math.sin(t * 2.6) * (HEIGHT * 0.28)
    return int(x), int(y)


def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    game = SnakeGame(width=WIDTH, height=HEIGHT, base_speed=10.0)

    gif_frames = []
    for i in range(FRAMES):
        t = i / 12.0
        target = fingertip_path(t)
        boosting = (i // 20) % 3 == 0
        state = game.update(target=target, hand_found=True, boosting=boosting)

        canvas = synthetic_background(t)
        ui.draw_food(canvas, state.food, t)
        ui.draw_snake(canvas, state.segments, state.boosting)
        ui.draw_fingertip_cursor(canvas, target, boosting)
        ui.draw_hud(canvas, state.score, state.high_score, state.boosting)

        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        gif_frames.append(rgb)

    imageio.mimsave(OUT_PATH, gif_frames, duration=0.05, loop=0)
    print(f"Wrote {len(gif_frames)}-frame demo GIF to {OUT_PATH}")


if __name__ == "__main__":
    main()

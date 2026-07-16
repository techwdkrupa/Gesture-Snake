"""
Gesture Snake
=============
Control a snake with your bare hand, using nothing but a webcam.

  - Move your INDEX FINGER to steer the snake.
  - PINCH (thumb + index together) to boost speed.
  - OPEN PALM pauses the game.
  - Press R to restart, Q to quit.

Run:
    python main.py

See README.md for setup details.
"""

import argparse
import time

import cv2

from src.game import SnakeGame, GameStatus
from src.hand_tracker import HandTracker
from src import ui


def parse_args():
    parser = argparse.ArgumentParser(description="Gesture-controlled Snake")
    parser.add_argument("--camera", type=int, default=0, help="Webcam device index (default: 0)")
    parser.add_argument("--width", type=int, default=960, help="Capture width")
    parser.add_argument("--height", type=int, default=540, help="Capture height")
    parser.add_argument("--mirror", action="store_true", default=True, help="Mirror the camera feed (on by default)")
    return parser.parse_args()


def main():
    args = parse_args()

    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    if not cap.isOpened():
        raise RuntimeError(
            "Could not open the webcam. Check that a camera is connected and "
            "that this app has camera permission."
        )

    ok, frame = cap.read()
    if not ok:
        raise RuntimeError("Webcam opened but returned no frames.")
    h, w = frame.shape[:2]

    try:
        tracker = HandTracker()
    except FileNotFoundError as exc:
        cap.release()
        print(f"\n{exc}\n")
        raise SystemExit(1)

    game = SnakeGame(width=w, height=h)

    window_name = "Gesture Snake  |  Q: quit   R: restart"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    start_time = time.time()

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            if args.mirror:
                frame = cv2.flip(frame, 1)

            hand_state = tracker.process(frame)

            target = hand_state.fingertip
            boosting = hand_state.is_pinching
            hand_found = hand_state.found and not hand_state.is_open_palm

            state = game.update(target=target, hand_found=hand_found, boosting=boosting)

            canvas = ui.darken(frame)
            ui.draw_food(canvas, state.food, time.time() - start_time)
            ui.draw_snake(canvas, state.segments, state.boosting)
            ui.draw_fingertip_cursor(canvas, hand_state.fingertip, hand_state.is_pinching)
            ui.draw_hud(canvas, state.score, state.high_score, state.boosting)
            ui.draw_status_overlay(canvas, state.status, state.score)

            cv2.imshow(window_name, canvas)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("r"):
                hs = game.high_score
                game.reset()
                game.high_score = hs
    finally:
        tracker.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

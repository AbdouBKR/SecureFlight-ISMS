import cv2
import mediapipe as mp
from collections import deque


# ========== SETUP HAND DETECTION ==========
def setup_hand_detection():
    """Initialize MediaPipe Hands (up to 2 hands) and the webcam capture"""
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    hands = mp_hands.Hands(min_detection_confidence=0.7, max_num_hands=2)
    cap = cv2.VideoCapture(0)
    return hands, cap, mp_hands, mp_drawing


# ========== GESTURE BUFFER FOR STABILITY ==========
class GestureBuffer:
    """
    Smooths out gesture recognition by storing the last N detections
    and returning the most common command, reducing jitter.
    """
    def __init__(self, size=5):
        self.buffer = deque(maxlen=size)

    def add(self, command):
        self.buffer.append(command)
        if len(self.buffer) < 3:
            return command
        return max(set(self.buffer), key=self.buffer.count)


# ========== COUNT FINGERS ==========
def count_fingers(hand_landmarks):
    """
    Count how many fingers are extended (0-5).
    Uses landmark positions relative to palm centre and PIP joints.
    Handles left and right hands separately for thumb detection.
    """
    fingers_up = 0

    thumb_tip   = hand_landmarks.landmark[4]
    thumb_mcp   = hand_landmarks.landmark[2]
    index_mcp   = hand_landmarks.landmark[5]
    palm_center = hand_landmarks.landmark[9]

    # Thumb: direction depends on which hand it is
    is_right_hand = thumb_mcp.x < index_mcp.x
    if is_right_hand:
        thumb_extended = thumb_tip.x < thumb_mcp.x - 0.04
    else:
        thumb_extended = thumb_tip.x > thumb_mcp.x + 0.04

    if thumb_extended:
        fingers_up += 1

    # Index, Middle, Ring, Pinky: tip must be above PIP and far from palm
    for tip_id in [8, 12, 16, 20]:
        tip = hand_landmarks.landmark[tip_id]
        pip = hand_landmarks.landmark[tip_id - 2]

        tip_above    = tip.y < pip.y
        tip_distance = ((tip.x - palm_center.x) ** 2 +
                        (tip.y - palm_center.y) ** 2) ** 0.5

        if tip_above and tip_distance > 0.08:
            fingers_up += 1

    return fingers_up


# ========== DETECT THUMBS DOWN ==========
def detect_thumbs_down(hand_landmarks):
    """
    Return True if the thumb is pointing downward and all other
    fingers are closed — used to trigger the DOWN command.
    """
    thumb_tip   = hand_landmarks.landmark[4]
    wrist       = hand_landmarks.landmark[0]
    palm_center = hand_landmarks.landmark[9]

    thumb_pointing_down = thumb_tip.y > wrist.y + 0.1

    fingers_closed = True
    for tip_id in [8, 12, 16, 20]:
        tip = hand_landmarks.landmark[tip_id]
        distance = ((tip.x - palm_center.x) ** 2 +
                    (tip.y - palm_center.y) ** 2) ** 0.5
        if distance > 0.12:
            fingers_closed = False
            break

    return thumb_pointing_down and fingers_closed


# ========== MAP FINGERS TO COMMAND (LEFT HAND) ==========
def fingers_to_command(finger_count):
    """Convert a finger count (0-5) to a drone movement command (left hand)"""
    mapping = {
        0: 'HOVER',
        1: 'FORWARD',
        2: 'BACKWARD',
        3: 'HOVER',
        4: 'HOVER',
        5: 'UP',
    }
    return mapping.get(finger_count, 'HOVER')


# ========== MAP FINGERS TO LATERAL COMMAND (RIGHT HAND) ==========
def fingers_to_lateral(finger_count):
    """
    Convert right hand finger count to a lateral command.
      0 fingers (fist) → no lateral movement
      1 finger         → LEFT
      2 fingers        → RIGHT
    """
    if finger_count == 1:
        return 'LEFT'
    elif finger_count == 2:
        return 'RIGHT'
    return None   # No lateral movement
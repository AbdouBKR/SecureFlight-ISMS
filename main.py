import time
import cv2
import pybullet as p
import hashlib

from simulation import (setup_simulation, update_drone_position,
                        draw_flight_trail, auto_takeoff, auto_land)
from gesture   import (setup_hand_detection, GestureBuffer,
                        count_fingers, detect_thumbs_down,
                        fingers_to_command, fingers_to_lateral)
from systems   import CameraSystem, WindSystem, PayloadSystem, LatencySystem
from auth      import authenticate, _hash, _load_db
from logger    import log_command

SESSION_TIMEOUT = 30   # Seconds before session auto-locks


# ========== RE-AUTHENTICATION POPUP ==========
def reauth_popup(username):
    """
    Show a tkinter popup asking the user to re-enter their password.
    Returns True if authentication succeeds, False if max attempts exceeded.

    Locked sessions require re-authentication to resume.
    """
    import tkinter as tk
    from tkinter import messagebox

    db       = _load_db()
    attempts = [0]
    success  = [False]

    root = tk.Tk()
    root.title("Session Locked")
    root.resizable(False, False)
    root.configure(bg="#1a1a2e")
    root.geometry("300x220")
    root.lift()
    root.attributes("-topmost", True)

    tk.Label(root, text="🔒  SESSION LOCKED",
             font=("Arial", 14, "bold"), bg="#1a1a2e", fg="#ff4444"
             ).pack(pady=(25, 5))

    tk.Label(root, text="Re-enter your password to resume",
             font=("Arial", 9), bg="#1a1a2e", fg="#aaaaaa"
             ).pack(pady=(0, 15))

    pass_entry = tk.Entry(root, font=("Arial", 11), width=22, show="•")
    pass_entry.pack(pady=(0, 5))
    pass_entry.focus()

    msg_label = tk.Label(root, text="", font=("Arial", 9),
                         bg="#1a1a2e", fg="#ff4444")
    msg_label.pack(pady=3)

    def attempt_unlock(event=None):
        credential = pass_entry.get()
        if username in db and db[username]["hash"] == _hash(credential):
            success[0] = True
            root.destroy()
            return
        attempts[0] += 1
        remaining = 3 - attempts[0]
        if remaining <= 0:
            messagebox.showerror("Access Denied",
                                 "Too many failed attempts. Exiting.")
            root.destroy()
        else:
            msg_label.config(text=f"Incorrect. {remaining} attempt(s) left.")
            pass_entry.delete(0, tk.END)

    pass_entry.bind("<Return>", attempt_unlock)
    tk.Button(root, text="Unlock", font=("Arial", 11),
              bg="#2e6db4", fg="white", relief="flat", width=14,
              command=attempt_unlock).pack(pady=8)

    root.mainloop()
    return success[0]


# ========== HANDLE KEYBOARD INPUT ==========
def handle_keyboard(drone, camera_system, wind_system, payload_system,
                    latency_system, role='user'):
    """
    Handle keyboard controls.
    Evaluation tests (F/P/X) are restricted to admin role only.

    Admin-only features are gated by role at runtime.
    """
    keys = p.getKeyboardEvents()

    if ord('t') in keys and keys[ord('t')] & p.KEY_WAS_TRIGGERED:
        print("🚁 AUTO TAKEOFF initiated...")
        auto_takeoff(drone, target_height=1.0)
        return 'takeoff'

    if ord('l') in keys and keys[ord('l')] & p.KEY_WAS_TRIGGERED:
        print("🛬 AUTO LANDING initiated...")
        auto_land(drone)
        return 'land'

    if ord('c') in keys and keys[ord('c')] & p.KEY_WAS_TRIGGERED:
        camera_system.toggle()
        return 'camera_toggle'

    # ── Admin-only evaluation tests ───────────────────────────────────────
    if role == 'admin':
        if ord('f') in keys and keys[ord('f')] & p.KEY_WAS_TRIGGERED:
            wind_system.toggle()
            return 'wind_toggle'

        if ord('p') in keys and keys[ord('p')] & p.KEY_WAS_TRIGGERED:
            payload_system.toggle(drone)
            return 'payload_toggle'

        if ord('x') in keys and keys[ord('x')] & p.KEY_WAS_TRIGGERED:
            latency_system.toggle()
            return 'latency_toggle'

    return None


# ========== MAIN ==========
def main():
    # ── Authentication — must pass before simulation loads ──────────────
    role, username = authenticate()

    print("=" * 70)
    print("       HAND GESTURE DRONE CONTROL - EVALUATION VERSION")
    print("=" * 70)
    print("LEFT HAND — Primary control:")
    print("  👊 Fist (0 fingers)  → HOVER")
    print("  👆 1 finger          → FORWARD")
    print("  ✌️  2 fingers         → BACKWARD")
    print("  🖐️  5 fingers         → UP")
    print("  👎 Thumbs DOWN       → DOWN")
    print()
    print("RIGHT HAND — Lateral control:")
    print("  👊 Fist (0 fingers)  → No lateral movement")
    print("  👆 1 finger          → LEFT")
    print("  ✌️  2 fingers         → RIGHT")
    print("  (Both hands together → DIAGONAL movement)")
    print()
    print("KEYBOARD CONTROLS:")
    print("  T → Auto Takeoff to 1m     L → Auto Land")
    print("  C → Toggle Camera (Third/First Person)")
    print("  Q → Quit (in OpenCV window)")
    print()
    print("EVALUATION TESTS (toggle on/off mid-flight):")
    print("  F → Test 1: WIND    — constant lateral force (+X axis)")
    print("  P → Test 2: PAYLOAD — doubles drone mass")
    print("  X → Test 3: LATENCY — adds 250 ms command delay")
    print()
    print("SAFETY FEATURES:")
    print("  ✓ Virtual Fence:     Max height 2.5m, Min height 0.5m")
    print("  ✓ Flight Trail:      Red line shows drone path")
    print("  ✓ Gesture Smoothing: Reduces jitter")
    print("=" * 70)

    # ── Initialise all subsystems ──────────────────────────────────────────
    drone, rings             = setup_simulation()
    hands, cap, mp_hands, mp_drawing = setup_hand_detection()
    left_buffer              = GestureBuffer(size=5)
    right_buffer             = GestureBuffer(size=5)
    camera_system            = CameraSystem()
    wind_system              = WindSystem(force_magnitude=3.0)
    payload_system           = PayloadSystem()
    latency_system           = LatencySystem(delay=0.25)

    prev_pos             = None
    frame_count          = 0
    last_logged_command  = None
    last_hand_time       = time.time()   # Tracks last detected hand for timeout
    locked               = False
    command         = 'HOVER'
    lateral_command = None
    finger_count    = 0
    last_results    = None

    print("\n🚁 Starting auto takeoff...")
    auto_takeoff(drone, target_height=1.0)

    # ── Main loop — runs at 60 fps ─────────────────────────────────────────
    while True:

        # ── Capture webcam frame ───────────────────────────────────────────
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)

        # ── Run MediaPipe only every 3rd frame ────────────────────────────
        if frame_count % 3 == 0:
            rgb_frame    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            last_results = hands.process(rgb_frame)

        command         = 'HOVER'
        lateral_command = None
        finger_count    = 0
        lateral_count   = 0

        # ── Process detected hands by handedness ──────────────────────────
        if last_results and last_results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(
                last_results.multi_hand_landmarks,
                last_results.multi_handedness
            ):
                mp_drawing.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                label = handedness.classification[0].label  # 'Left' or 'Right'

                if label == 'Left':
                    # Left hand → primary command (forward/back/up/down)
                    if detect_thumbs_down(hand_landmarks):
                        command      = left_buffer.add('DOWN')
                        finger_count = -1
                    else:
                        finger_count = count_fingers(hand_landmarks)
                        command      = left_buffer.add(
                                           fingers_to_command(finger_count))

                elif label == 'Right':
                    # Right hand → lateral command (left/right)
                    lateral_count   = count_fingers(hand_landmarks)
                    lateral_command = right_buffer.add(
                                          fingers_to_lateral(lateral_count) or 'NONE')
                    if lateral_command == 'NONE':
                        lateral_command = None

        # ── Session timeout check ─────────────────────────────────────────
        if last_results and last_results.multi_hand_landmarks:
            last_hand_time = time.time()   # Reset timer when hand is seen

        if not locked and (time.time() - last_hand_time) > SESSION_TIMEOUT:
            locked  = True
            command = 'HOVER'
            print("\n🔒 Session locked — no hand detected for 30 seconds.")

        if locked:
            # Show lock screen over the webcam feed
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]),
                          (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
            cv2.putText(frame, '🔒 SESSION LOCKED',
                        (60, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
            cv2.putText(frame, 'Enter password in terminal',
                        (55, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.imshow('Hand Gesture Control', frame)
            cv2.waitKey(1)

            # Re-authenticate via GUI popup
            if reauth_popup(username):
                locked         = False
                last_hand_time = time.time()
                print("✓ Session unlocked.")
            else:
                print("✗ Too many failed attempts. Exiting.")
                break

            continue   # Skip rest of loop while locked

        # ── Draw HUD overlay ───────────────────────────────────────────────
        pos, _ = p.getBasePositionAndOrientation(drone)

        cv2.rectangle(frame, (5, 5), (310, 200), (0, 0, 0), -1)

        # Left hand status
        if finger_count == -1:
            cv2.putText(frame, 'L: THUMBS DOWN',
                        (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 100, 0), 2)
        else:
            cv2.putText(frame, f'L: {finger_count} fingers',
                        (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # Right hand status
        lat_label = lateral_command if lateral_command else 'NONE'
        cv2.putText(frame, f'R: {lateral_count} fingers  ({lat_label})',
                    (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)

        # Combined command
        cmd_color = (0, 255, 255) if command != 'HOVER' or lateral_command else (100, 100, 100)
        cv2.putText(frame, f'CMD: {command}',
                    (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.9, cmd_color, 2)

        cv2.putText(frame, f'Height: {pos[2]:.2f}m',
                    (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        fence_color = (0, 0, 255) if pos[2] >= 2.4 or pos[2] <= 0.6 else (0, 255, 0)
        cv2.putText(frame, 'Max: 2.5m | Min: 0.5m',
                    (10, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.6, fence_color, 2)

        cv2.imshow('Hand Gesture Control', frame)

        # ── Update drone physics ───────────────────────────────────────────
        wind_drift = wind_system.get_drift()
        new_pos    = update_drone_position(drone, command,
                                           lateral_command=lateral_command,
                                           wind_drift=wind_drift,
                                           payload_active=payload_system.active)

        draw_flight_trail(prev_pos, new_pos)
        prev_pos = new_pos

        # ── Audit log — only log when command changes, skip HOVER ─────────
        # Audit log — only log when command changes, skip HOVER
        if command != 'HOVER' and command != last_logged_command:
            log_command(username, command)
            last_logged_command = command

        # ── Keyboard and camera ────────────────────────────────────────────
        handle_keyboard(drone, camera_system, wind_system, payload_system,
                        latency_system, role=role)

        # Update camera every 10 frames — same as original working code
        if frame_count % 10 == 0:
            camera_system.update(new_pos)

        p.stepSimulation()

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\n🛑 Quitting...")
            break

        time.sleep(1. / 60)
        latency_system.apply()

        frame_count += 1

    # ── Cleanup ────────────────────────────────────────────────────────────
    cap.release()
    cv2.destroyAllWindows()
    p.disconnect()
    print("✓ Simulation ended.")


if __name__ == "__main__":
    main()
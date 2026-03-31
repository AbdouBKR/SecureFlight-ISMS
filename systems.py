import time
import cv2
import pybullet as p


# ========== CAMERA SYSTEM ==========
class CameraSystem:
    """Manages third-person and first-person PyBullet camera views"""

    def __init__(self):
        self.mode = 'third_person'

    def toggle(self):
        if self.mode == 'third_person':
            self.mode = 'first_person'
            print("📷 Camera: FIRST-PERSON VIEW (Drone POV)")
        else:
            self.mode = 'third_person'
            print("📷 Camera: THIRD-PERSON VIEW")

    def update(self, drone_pos):
        if self.mode == 'third_person':
            p.resetDebugVisualizerCamera(
                cameraDistance=5,
                cameraYaw=50,
                cameraPitch=-35,
                cameraTargetPosition=drone_pos
            )
        elif self.mode == 'first_person':
            p.resetDebugVisualizerCamera(
                cameraDistance=0.1,
                cameraYaw=0,
                cameraPitch=0,
                cameraTargetPosition=drone_pos
            )


# ========== TEST 1: WIND SIMULATION ==========
class WindSystem:
    """
    EVALUATION TEST 1: Wind / External Force
    Applies a constant lateral drift to the drone on every frame,
    simulating a steady breeze. Toggle on/off with F key.
    """

    def __init__(self, force_magnitude=3.0):
        self.active = False
        self.force = [force_magnitude, 0, 0]  # Wind blows in +X direction

    def toggle(self):
        self.active = not self.active
        state = "ON 💨" if self.active else "OFF"
        print(f"\n[TEST 1 - WIND] Wind is now {state}")
        if self.active:
            print(f"  Applying constant force {self.force} N in +X direction")
            print("  OBSERVATION: Does the drone drift? How hard is it to correct?")

    def get_drift(self):
        """Return the per-frame positional drift vector, or None if inactive"""
        if self.active:
            return [f * 0.003 for f in self.force]
        return None

    def overlay(self, frame):
        """Draw wind status indicator on the OpenCV HUD"""
        color = (0, 200, 255) if self.active else (80, 80, 80)
        label = f"WIND:    {'ON  >>>' if self.active else 'OFF'}"
        cv2.putText(frame, label, (10, 210),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)


# ========== TEST 2: PAYLOAD (MASS) SIMULATION ==========
class PayloadSystem:
    """
    EVALUATION TEST 2: Payload / Increased Mass
    Doubles the drone's mass using p.changeDynamics and causes a
    slow continuous sink to simulate carrying extra weight.
    Toggle on/off with P key.
    """

    def __init__(self):
        self.active = False
        self.base_mass  = None
        self.heavy_mass = None

    def toggle(self, drone):
        if self.base_mass is None:
            self.base_mass  = p.getDynamicsInfo(drone, -1)[0]
            self.heavy_mass = self.base_mass * 2.0

        self.active = not self.active

        if self.active:
            p.changeDynamics(drone, -1, mass=self.heavy_mass)
            print(f"\n[TEST 2 - PAYLOAD] Payload ON — mass doubled to {self.heavy_mass:.2f}kg")
            print("  OBSERVATION: Does the drone sink? Is UP harder to maintain?")
        else:
            p.changeDynamics(drone, -1, mass=self.base_mass)
            print(f"\n[TEST 2 - PAYLOAD] Payload OFF — mass restored to {self.base_mass:.2f}kg")

    def overlay(self, frame, drone):
        """Draw payload status indicator on the OpenCV HUD"""
        color = (255, 100, 0) if self.active else (80, 80, 80)
        mass_str = f"{self.heavy_mass:.1f}kg" if self.active and self.heavy_mass else "normal"
        label = f"PAYLOAD: {'ON  x2 mass (' + mass_str + ')' if self.active else 'OFF'}"
        cv2.putText(frame, label, (10, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)


# ========== TEST 3: LATENCY (LAG) SIMULATION ==========
class LatencySystem:
    """
    EVALUATION TEST 3: Command Latency / WiFi Lag
    Inserts a time.sleep() delay per frame to simulate a 250 ms
    WiFi round-trip delay. Toggle on/off with X key.
    """

    def __init__(self, delay=0.10):
        self.active = False
        self.delay  = delay

    def toggle(self):
        self.active = not self.active
        state = "ON ⏳" if self.active else "OFF"
        print(f"\n[TEST 3 - LATENCY] {self.delay * 1000:.0f}ms lag is now {state}")
        if self.active:
            print("  OBSERVATION: Does over-correction happen? Hard to stabilise?")

    def apply(self):
        """Insert the configured delay if the test is active"""
        if self.active:
            time.sleep(self.delay)

    def overlay(self, frame):
        """Draw latency status indicator on the OpenCV HUD"""
        color = (0, 80, 255) if self.active else (80, 80, 80)
        label = f"LATENCY: {'ON  +250ms lag' if self.active else 'OFF'}"
        cv2.putText(frame, label, (10, 270),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
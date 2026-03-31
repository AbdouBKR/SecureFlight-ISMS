import pybullet as p
import pybullet_data
import time
import math


# ========== CREATE A SINGLE RING ==========
def create_ring(cx, cy, cz, radius=1.2, num_spheres=28, sphere_radius=0.1):
    """
    Build a visual ring in the air from small red spheres arranged in a circle.
    The ring lies in the XZ plane (vertical, facing the Y axis) so the drone
    flies through it along the Y direction.
    """
    sphere_ids = []
    visual_shape = p.createVisualShape(
        p.GEOM_SPHERE,
        radius=sphere_radius,
        rgbaColor=[1, 0, 0, 1]
    )

    for i in range(num_spheres):
        angle = 2 * math.pi * i / num_spheres
        x = cx + radius * math.cos(angle)
        y = cy
        z = cz + radius * math.sin(angle)

        body = p.createMultiBody(
            baseMass=0,
            baseCollisionShapeIndex=-1,   # Pure visual — zero physics overhead
            baseVisualShapeIndex=visual_shape,
            basePosition=[x, y, z]
        )
        sphere_ids.append(body)

    return sphere_ids


# ========== SETUP PYBULLET ==========
def setup_simulation():
    """Initialize PyBullet, load the drone, and create the aerial ring course"""
    p.connect(p.GUI)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.loadURDF("plane.urdf")
    p.setGravity(0, 0, -9.8)

    drone = p.loadURDF("r2d2.urdf", [0, 0, 1])

    ring_positions = [
        ( 0.0,  4.0, 1.5),
        ( 0.8,  8.0, 2.3),
        (-0.8, 12.0, 1.0),
        ( 0.6, 16.0, 2.2),
        ( 0.0, 20.0, 1.5),
    ]

    rings = []
    for i, (rx, ry, rz) in enumerate(ring_positions):
        ring_spheres = create_ring(rx, ry, rz)
        rings.append(ring_spheres)
        print(f"  Ring {i + 1} at ({rx}, {ry}, {rz})")

    print(f"✓ Ring course created — {len(rings)} rings placed!")

    return drone, rings


# ========== VIRTUAL FENCE (SAFETY FEATURE) ==========
def apply_virtual_fence(pos, command, max_height=2.5, min_height=0.5):
    """
    SAFETY FEATURE: Enforce flight boundaries.
    - Maximum height: 2.5m  /  Minimum height: 0.5m
    """
    if command == 'UP' and pos[2] >= max_height:
        return 'HOVER'
    if command == 'DOWN' and pos[2] <= min_height:
        return 'HOVER'
    return command


# ========== UPDATE DRONE POSITION ==========
def update_drone_position(drone, command, lateral_command=None,
                          wind_drift=None, payload_active=False):
    """
    Move drone based on primary command (left hand) and optional
    lateral command (right hand). Both are applied in the same step,
    producing true diagonal movement when both are active.
    """
    pos, orn = p.getBasePositionAndOrientation(drone)

    command = apply_virtual_fence(pos, command)

    speed    = 0.05
    new_pos  = list(pos)

    # ── Primary command (left hand) ───────────────────────────────────────
    if command == 'FORWARD':
        new_pos[1] += speed
    elif command == 'BACKWARD':
        new_pos[1] -= speed
    elif command == 'UP':
        new_pos[2] += speed
    elif command == 'DOWN':
        new_pos[2] -= speed

    # ── Lateral command (right hand) ──────────────────────────────────────
    if lateral_command == 'LEFT':
        new_pos[0] -= speed
    elif lateral_command == 'RIGHT':
        new_pos[0] += speed

    # Payload: drone slowly sinks due to extra weight
    if payload_active:
        new_pos[2] -= 0.008

    if wind_drift:
        new_pos[0] += wind_drift[0]
        new_pos[1] += wind_drift[1]
        new_pos[2] += wind_drift[2]

    # Hard clamp as a final safety net
    new_pos[2] = max(0.5, min(new_pos[2], 2.5))

    p.resetBasePositionAndOrientation(drone, new_pos, orn)
    return new_pos


# ========== FLIGHT TRAIL ==========
def draw_flight_trail(prev_pos, current_pos):
    """Draw a fading trail line showing the drone's recent path"""
    if prev_pos is not None:
        p.addUserDebugLine(
            prev_pos,
            current_pos,
            lineColorRGB=[1, 0, 0],
            lineWidth=3,
            lifeTime=0
        )


# ========== AUTONOMOUS ACTIONS ==========
def auto_takeoff(drone, target_height=1.0, speed=0.02):
    """Smoothly lift the drone to the target height"""
    while True:
        pos, orn = p.getBasePositionAndOrientation(drone)
        if pos[2] >= target_height:
            break
        new_pos = [pos[0], pos[1], pos[2] + speed]
        p.resetBasePositionAndOrientation(drone, new_pos, orn)
        p.stepSimulation()
        time.sleep(1. / 240)
    print(f"✓ Takeoff complete! Hovering at {target_height}m")


def auto_land(drone, speed=0.02):
    """Smoothly descend the drone to the minimum safe height"""
    while True:
        pos, orn = p.getBasePositionAndOrientation(drone)
        if pos[2] <= 0.5:
            break
        new_pos = [pos[0], pos[1], pos[2] - speed]
        p.resetBasePositionAndOrientation(drone, new_pos, orn)
        p.stepSimulation()
        time.sleep(1. / 240)
    print("✓ Landing complete!")
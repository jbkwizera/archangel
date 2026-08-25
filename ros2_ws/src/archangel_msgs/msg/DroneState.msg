# Periodic state report published by each drone.

# Status enum (ROS 2 has no native enums; use uint8 constants).
uint8 IDLE=0
uint8 TAKING_OFF=1
uint8 EN_ROUTE=2
uint8 LOITERING=3
uint8 RETURNING=4
uint8 LANDING=5

std_msgs/Header header        # stamp + frame_id
uint8 drone_id                # which drone this state belongs to
geometry_msgs/Point position  # current position (x, y, z) in the world frame, metres
float32 battery               # remaining battery fraction, 0.0-1.0
uint8 status                  # one of the status constants above

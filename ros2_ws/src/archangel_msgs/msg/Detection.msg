# A single intruder detection reported by a drone.
std_msgs/Header header        # stamp + frame_id
uint8 drone_id                # drone that made the detection
geometry_msgs/Point position  # estimated intruder position (x, y, z), world frame, metres
float32 confidence            # detection confidence, 0.0-1.0

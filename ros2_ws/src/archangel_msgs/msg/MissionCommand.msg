# A mission assigned to a single drone: an ordered list of waypoints to fly.
std_msgs/Header header      # stamp + frame_id
uint32 mission_id           # unique id for this mission
uint8 drone_id              # target drone this mission is addressed to
Waypoint[] waypoints        # ordered waypoints to visit

from arm_communicator import ArmCommunicator
import math
import time
from kinematics import *

try:
    osc_client = ArmCommunicator(fps=100)
    i = 0
    while(True):
        con = 70 * math.sin(i / 100)
        angles = np.array((0, 0, 0, 0))
        print(f"ee: {solve_FK(angles, 0.338, 0.284, True)}")
        osc_client.update_directive("/armR", angles)
        i += 1
        time.sleep(0.01)
finally:
    osc_client.close()
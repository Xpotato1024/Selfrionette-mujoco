from arm_communicator import ArmCommunicator
import math
import time
from kinematics import *
from mouse_monitor import MouseMonitor

L1 = 0.338
L2 = 0.27

ref_pos = np.array([0.4, 0., 0., 0.])
pos = ref_pos.copy()
#pos = np.array([0.4, 0.2, 0, -90])
angles=solve_IK(pos, L1, L2)
#angles[0:3] = another_sholder_joint_angles(angles[0:3])
pre_angles = angles
print("j: %5.1f %5.1f %5.1f %5.1f" % tuple(angles * 180.0 / math.pi), end="\n")

try:
    mm = MouseMonitor(np.array((0.0002, 0.0004, 0.07)))
    mm.start()
    osc_client = ArmCommunicator(fps=100, init_joint_angles=angles, max_angle_change=4000)
    osc_client.update_directive("/armR", angles * 180.0 / math.pi)
    time.sleep(1)
    i = 0
    while(i < 5000):
        x, z, y = mm.get()
        pos[0], pos[1], pos[2] = x, y, -z
        pos[0:3] = ref_pos[0:3] + pos[0:3]
        #pos[0] = 0.4 + 0.15 * math.sin(i / 100)
        #pos[1] = 0.2 * math.cos(i / 30)
        #pos[2] = 0.3 * math.sin(i / 20)
        #pos[3] = math.pi / 2.0 * math.sin(i / 100)
        angles = solve_IK(pos, L1, L2)
        #angles[0] = 0
        # NOTE: より近い解を用いる
        # 肩のオイラー角の別解を用いるか？
        another = another_sholder_joint_angles(angles[0:3])
        # print("j: %5.1f %5.1f %5.1f %5.1f" % tuple(angles * 180.0 / math.pi), end=" / ")
        # print("a: %5.1f %5.1f %5.1f" % tuple(another * 180.0 / math.pi), end=" / ")
        one_sum = np.abs(angles[0:3] - pre_angles[0:3]).sum()
        ano_sum = np.abs(another - pre_angles[0:3]).sum()
        if(ano_sum < one_sum):
            angles[0:3] = another
            #print(" (a) ", end="")
        #else:
            #print(" (j) ", end="")
        err = angles - pre_angles
        # if(np.count_nonzero(np.abs(err) > math.pi / 2.0)):
        #     another = another_sholder_joint_angles(angles[0:3])
        #     another_err = another - pre_angles[0:3]
        #     if(np.count_nonzero(np.abs(another_err) > math.pi / 2.0)):
        #         pass
        #     else:
        #         err[0:3] = another_err
        #         angles[0:3] = another
        # -180 ~ 180の範囲外になったか？
        # for j in range(len(angles)):
        #     if(abs(err[j]) > math.pi):
        #         if(angles[j] < 0):
        #             angles[j] += math.pi * 2.0
        #         else:
        #             angles[j] -= math.pi * 2.0
        #         err[j] = angles[j] - pre_angles[j]
        #         # angles = pre_angles
        #         # err = angles - pre_angles
        #         break
        #print("joint: %5.1f %5.1f %5.1f %5.1f" % tuple(angles * 180.0 / math.pi), end=" ")
        print("pos: %5.3f %5.3f %5.3f %5.3f" % (pos[0], pos[1], pos[2], pos[3] * 180.0 / math.pi))
        print(f"   err: {err}")
        if(np.count_nonzero(np.abs(err) > math.pi / 2.0)):
            print("!!! Danger !!!", end="")
            a = input()
            i += 1
            continue
        osc_client.update_directive("/armR", angles * 180.0 / math.pi)
        i += 1
        time.sleep(0.01)
        pre_angles = angles
finally:
    mm.stop()
    osc_client.close()
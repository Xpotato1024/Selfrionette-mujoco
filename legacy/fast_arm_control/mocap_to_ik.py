# mocap -> IK -> arm joint angles

import time
import math
import numpy as np
from pyquaternion import Quaternion
from scipy.spatial.transform import Rotation
from kinematics import FastArmKinematics
import signal
from mocap_to_joint.NatNetClient import NatNetClient
from mocap_to_joint.arm_communicator import ArmCommunicator
from ik_controller import IKController

# fast armのリンク長[m]
L1 = 0.338
L2 = 0.284

# Motive (NatNet)
LOCAL_IP = "127.0.0.1"
MOTIVE_IP = "127.0.0.1"
MOCAP_FPS = 120.0
BASE_RIGID_BODY_ID = 1
TIP_RIGID_BODY_ID = 2

## OSC: Send joint angles
SEND_OSC_IP = "127.0.0.1"
SEND_OSC_PORT = "5555"

OFFSET_ANGLE = -math.pi / 4
OFFSET_ROT = np.array([[math.cos(OFFSET_ANGLE), -math.sin(OFFSET_ANGLE), 0], 
                       [math.sin(OFFSET_ANGLE),  math.cos(OFFSET_ANGLE), 0], 
                       [0, 0, 1]])

kinematics = FastArmKinematics(L1, L2, (0.1, 0.62), q2_offset=True)
current_joint_angles = np.array([0.0, 0.0, 0.0, 0.0])
controller = IKController(kinematics, init_angle=current_joint_angles)
controller.set_joint_angle_limit(
    np.array([[-math.pi, math.pi], [-math.pi, math.pi], 
              [-math.pi, math.pi], [-math.pi, math.pi]]))
controller.set_joint_speed_limit(np.array([3.0, 3.0, 3.0, 3.0]), MOCAP_FPS)     # rad/s

# mocapデータ受信時のコールバック
def receive_new_frame_callback( frameNumber, timestamp, rigid_bodies):
    global tip_init_pos, tip_init_quat, send_angles_osc_client
    global kinematics, current_joint_angles
    #print( "Received frame", frameNumber )
    #print(f"timestamp     : {timestamp}")
    #print(rigid_bodies)
    recv_body_num = 0
    tip_pos = None
    tip_quat = Quaternion(1, 0, 0, 0)
    for body in rigid_bodies:
        if(body["id"] == TIP_RIGID_BODY_ID):
            recv_body_num += 1
            p = body["position"]
            q = body["rotation"]
            tip_pos = np.array((p[2], p[0], p[1]))
            tip_quat = Quaternion(q[3], q[2], q[0], q[1])
    if(recv_body_num < 1):
        return
    if(not receive_new_frame_callback.is_init):
        # 初回受信時は零点合わせ
        receive_new_frame_callback.is_init = True
        tip_init_pos = tip_pos
        tip_init_pos[2] += 0.62
        tip_init_quat = tip_quat
        print("Set Init Pose.")
        return
    # # 零点基準の姿勢に変換
    q = tip_init_quat.inverse * tip_quat
    p = tip_init_quat.inverse.rotate(tip_pos - tip_init_pos)
    #print(f"p:{p}, q:{q}")
    # 肘の仰角(Arm Angle)を出す
    # x, y, z = p
    # n0 = np.array([-y, x, 0])       # 基準平面の法線ベクトル(z軸を含む平面)
    tip_rot = Rotation.from_quat(np.roll(q.elements, -1)).as_matrix()
    n1 = tip_rot[:, 1]   # 腕平面の法線ベクトル
    # print("tip : (%5.3f, %5.3f, %5.3f)" % (p[0], p[1], p[2]))
    try:
        normal_pos = np.array((-p[1], p[0], p[2]))
        normal_nv = np.array((-n1[1], n1[0], n1[2]))
        current_joint_angles = controller.output(OFFSET_ROT @ normal_pos, OFFSET_ROT @ normal_nv)
    except ValueError as e:
        print(e)
        return
    send_angles_osc_client.update_directive("/armR", current_joint_angles * 180.0 / math.pi)
receive_new_frame_callback.is_init = False

# 後処理
def end_process():
    global send_angles_osc_client, recv_mocap_client
    recv_mocap_client.close()
    send_angles_osc_client.close()
    pass

# =============================== main setup ====================================

signal.signal(signal.SIGINT, lambda signum, handler: end_process())
init_flag = False
print("Setup Send Angles OSC ...")
send_angles_osc_client = ArmCommunicator(fps=120.0)
print("Setup NatNetClient ...")
recv_mocap_client = NatNetClient(LOCAL_IP, MOTIVE_IP)
recv_mocap_client.rigidBodyListener = receive_new_frame_callback
time.sleep(1)
try:
    recv_mocap_client.run()
    print("Start Main Loop. To Exit, input Ctrl+C.")
    while(not recv_mocap_client.is_end()):
        time.sleep(0.1)
finally:
    end_process()
import math
import numpy as np
import threading
import time
import signal
from kinematics import FastArmKinematics
from ik_controller import IKController
from mocap_to_joint.arm_communicator import ArmCommunicator

from pythonosc import dispatcher
from pythonosc import osc_server

FPS = 100

L1 = 0.338
L2 = 0.284 + 0.21  # 前腕リンク長 + ラクロスの半分ぐらい

R_MIN = 0.28
R_MAX = 0.825

# joint speed profile [rad/s]
SLOW_PROF = np.array([1.0, 1.0, 1.0, 1.0])
FAST_PROF = np.array([9.0, 9.0, 9.0, 6.0])

# キャッチの構えの姿勢の際の関節角
PREPOSE_JOINT_ANGLES = np.array([-5.3, -28.7, 46.9, 129.7]) * math.pi / 180.0

kinematics = FastArmKinematics(L1, L2, (R_MIN, R_MAX), q2_offset=True)
current_joint_angles = np.array([0.0, 0.0, 0.0, 0.0])
controller = IKController(kinematics, init_angle=current_joint_angles)
controller.set_joint_angle_limit(
    np.array([[-math.pi, math.pi], [-math.pi, 0.0], 
              [-math.pi, math.pi], [-math.pi, math.pi]]))
controller.set_joint_speed_limit(SLOW_PROF, FPS)

# ball tracking 受信
def recv_ball_pos(addr, *p):
    x, y, z, vx, vy, vz, arrival_time = p
    ball_pos, ball_vel = tracking_transform(np.array([x, y, z]), np.array([vx, vy, vz]))
    #print(f"ball_pos: {ball_pos}, ball_vel: {ball_vel}")
    check_ball_within_range(ball_pos, ball_vel)

# 後処理
def end_process():
    global end_flag
    end_flag = True

def tracking_transform(ball_pos: np.ndarray, ball_vel: np.ndarray):
    """ボールトラッキング座標からロボット座標への変換
    Args:
        ball_pos (np.ndarray): ボールトラッキング座標での位置
        ball_vel (np.ndarray): ボールトラッキング座標での速度
    Returns:
        np.ndarray: ロボット座標での位置
        np.ndarray: ロボット座標での速度
    """
    print(f"raw_recv_pos: {ball_pos}")
    offset = np.array([-0.070, 0.070, 0.080])
    rot_z_angle = math.pi / 4
    c = math.cos(rot_z_angle)
    s = math.sin(rot_z_angle)
    rot_z = np.array([[c, -s, 0], 
                      [s,  c, 0], 
                      [0,  0, 1]])
    return rot_z @ (ball_pos + offset), rot_z @ ball_vel

def check_ball_within_range(ball_pos: np.ndarray, ball_vel: np.ndarray):
    RANGE_MIN = R_MIN
    RANGE_MAX = R_MAX
    x, y, z = ball_pos
    r2 = x**2 + y**2 + z**2
    if(RANGE_MIN**2 < r2 < RANGE_MAX**2 and x > 0):
        print("ball is within range of arm motion.")
        global controller, current_joint_angles
        tip_pos = np.array([x, y, z, 0])
        nv = np.cross(ball_vel, tip_pos[0:3])
        nv_norm = np.linalg.norm(nv)
        if(nv_norm < 1e-12): return
        arm_plane_nv = nv / nv_norm
        current_joint_angles = controller.output(tip_pos[0:3], arm_plane_nv)
        #print(f"tip_pos : {tip_pos}, nv: {arm_plane_nv}")
    else:
        # None
        return

def arm_update():
    global end_flag, current_joint_angles
    while(not end_flag):
        send_angles_osc_client.update_directive("/armR", current_joint_angles * 180.0 / math.pi)
        #print(current_joint_angles)
        time.sleep(1.0 / FPS)
    
# =============================== main setup ====================================

end_flag = False
signal.signal(signal.SIGINT, lambda signum, handler: end_process())
init_flag = False

print("Setup Send Angles OSC ...")
send_angles_osc_client = ArmCommunicator(fps=FPS)
osc_send_thread = threading.Thread(target = arm_update, daemon = True)
osc_send_thread.start()
# 初期姿勢まで移動する
print("Set Init Pose")
controller.set_joint_speed_limit(SLOW_PROF, FPS)
for i in range(400):
    current_joint_angles = controller.angle_to_output(PREPOSE_JOINT_ANGLES.copy())
    time.sleep(0.01)
controller.set_joint_speed_limit(FAST_PROF, FPS)

print("Setup Recv Ball Tracking OSC")
disp = dispatcher.Dispatcher()
disp.map("/ball_pred", recv_ball_pos)
osc_receiver = osc_server.ThreadingOSCUDPServer(("127.0.0.1", 10001), disp)
osc_receive_th = threading.Thread(target = osc_receiver.serve_forever, daemon=True)
osc_receive_th.start()
time.sleep(1)

try:
    print("\n\n======================================\n\n")
    print("Start Main Loop. To Exit, input Ctrl+C. ")
    print("\n\n======================================\n\n")
    while not end_flag:
        time.sleep(0.1)
finally:
    osc_receiver.shutdown()
    osc_receive_th.join()
    send_angles_osc_client.close()
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
L2 = 0.284

kinematics = FastArmKinematics(L1, L2, (0.1, 0.62), q2_offset=True)
current_joint_angles = np.array([0.0, 0.0, 0.0, 0.0])
controller = IKController(kinematics, init_angle=current_joint_angles)
controller.set_joint_angle_limit(
    np.array([[-math.pi, math.pi], [-math.pi, math.pi], 
              [-math.pi, math.pi], [-math.pi, math.pi]]))
controller.set_joint_speed_limit(np.array([3.0, 3.0, 3.0, 3.0]), FPS)     # rad/s

tip_pos = np.array([0, 0, -0.62, 0])

# ball tracking 受信
def recv_ball_pos(addr, *p):
    x, y, z, is_track = p
    if not is_track:
        return
    ball_pos = tracking_transform(np.array([x, y, z]))
    print(ball_pos)
    check_ball_within_range(ball_pos)

# 後処理
def end_process():
    global end_flag, osc_receive_th, osc_receiver
    end_flag = True
    osc_receiver.shutdown()
    osc_receive_th.join()
    send_angles_osc_client.close()
    pass

def tracking_transform(ball_pos: np.ndarray):
    """ボールトラッキング座標からロボット座標への変換
    Args:
        ball_pos (np.ndarray): ボールトラッキング座標
    Returns:
        np.ndarray: ロボット座標
    """
    offset = np.array([-0.050, 0.120, 0.080])
    axis_change = np.array([[0, 0, 1], 
                            [1, 0, 0], 
                            [0, 1, 0]])
    rot_z_angle = math.pi / 4
    c = math.cos(rot_z_angle)
    s = math.sin(rot_z_angle)
    rot_z = np.array([[c, -s, 0], 
                      [s,  c, 0], 
                      [0,  0, 1]])
    return rot_z @ (axis_change @ ball_pos + offset)

def check_ball_within_range(ball_pos: np.ndarray):
    RANGE_MIN = 0.20
    RANGE_MAX = 0.60
    x, y, z = ball_pos
    z -= 0.10 # offset
    r2 = x**2 + y**2 + z**2
    if(RANGE_MIN**2 < r2 < RANGE_MAX**2 and x > 0 and z < 0):
        print("ball is within range of arm motion.")
        global tip_pos
        tip_pos[0] = x
        tip_pos[1] = y
        tip_pos[2] = z
    else:
        # None
        return

def arm_update():
    global controller, tip_pos, end_flag
    while(not end_flag):
        print(tip_pos)
        ik_output = controller.output(tip_pos)
        send_angles_osc_client.update_directive("/armR", ik_output * 180.0 / math.pi)
        time.sleep(1.0 / FPS)
    
# =============================== main setup ====================================

end_flag = False
#signal.signal(signal.SIGINT, lambda signum, handler: end_process())
init_flag = False
print("Setup Send Angles OSC ...")
send_angles_osc_client = ArmCommunicator(fps=FPS)

print("Setup Recv Ball Tracking OSC")
disp = dispatcher.Dispatcher()
disp.map("/ball_tracking", recv_ball_pos)
osc_receiver = osc_server.ThreadingOSCUDPServer(("127.0.0.1", 10000), disp)
osc_receive_th = threading.Thread(target = osc_receiver.serve_forever, daemon=True)
osc_receive_th.start()
osc_send_thread = threading.Thread(target = arm_update, daemon = True)
osc_send_thread.start()
time.sleep(1)

try:
    print("Start Main Loop. To Exit, input Ctrl+C. ")
    while True:
        time.sleep(0.1)
finally:
    osc_receiver.shutdown()
    osc_receive_th.join()
    send_angles_osc_client.close()
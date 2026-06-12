from NatNetClient import NatNetClient
import signal
import time
import sys

import math
import numpy as np
from pyquaternion import Quaternion
from scipy.spatial.transform import Rotation
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from mpl_toolkits.mplot3d import Axes3D
import geometry

import time

from arm_communicator import ArmCommunicator

OSC_IP = "127.0.0.1"
OSC_PORT = 5555

MOCAP_FPS = 240.0
VIEW_FPS = 30

def receiveNewFrame( frameNumber, timestamp, rigid_bodies):
    global arm_pos, hand_pos, arm_rot, hand_rot, hand_init_rot, arm_init_rot, init_flag, hand_init_pos, arm_init_pos
    #print( "Received frame", frameNumber )
    print(f"timestamp     : {timestamp}")
    #print(rigid_bodies)
    detect_num = 0
    for body in rigid_bodies:
        if(body["id"] == 1):
            detect_num += 1
            p = body["position"]
            q = body["rotation"]
            arm_pos = (p[2], p[0], p[1])
            arm_rot = Quaternion(q[3], q[2], q[0], q[1])
        elif(body["id"] == 2):
            detect_num += 1
            p = body["position"]
            q = body["rotation"]
            hand_pos = (p[2], p[0], p[1])
            hand_rot = Quaternion(q[3], q[2], q[0], q[1])
    if(detect_num >= 2):
        global hand_diff_rot, arm_diff_rot, arm2hand_rot, arm_euler, arm2hand_euler, osc_client
        if(init_flag == False):
            hand_init_rot = hand_rot
            arm_init_rot = arm_rot
            hand_init_pos = hand_pos
            arm_init_pos = arm_pos
            hand_diff_rot = hand_init_rot.inverse * hand_rot
            arm_diff_rot = arm_init_rot.inverse * arm_rot
            arm2hand_rot = arm_diff_rot.inverse * hand_diff_rot
            init_flag = True
        else:
            hand_diff_rot = hand_init_rot.inverse * hand_rot
            arm_diff_rot = arm_init_rot.inverse * arm_rot
            arm2hand_rot = arm_diff_rot.inverse * hand_diff_rot
            arm_euler = to_euler("zxy", arm_diff_rot)
            arm2hand_euler = to_euler("zyz", arm2hand_rot)
            joint_angles = (-arm_euler[2], arm_euler[1], -arm_euler[0], arm2hand_euler[1])
            osc_client.update_directive("/armR", joint_angles)

def to_euler(seq: str, quaternion: Quaternion) -> np.ndarray:
    return Rotation.from_quat(np.roll(quaternion.elements, -1)).as_euler(seq, degrees=True)

def norm_deg(deg):
    while(deg >= 180):
        deg -= 360
    while(deg < -180):
        deg += 360
    return deg

def plt_onkey(key_event):
    if(key_event.key == 'q'):
        streamingClient.close()

def plt_onclose(event):
    streamingClient.close()

# =============================== main setup ====================================

local_ip = "127.0.0.1"
server_ip = "127.0.0.1"
if(len(sys.argv) < 3):
    print("Require 2 parameters : [Local IP] [Server(Motive PC) IP]")
    print("Set Default 127.0.0.1 127.0.0.1")
else:
    local_ip = sys.argv[1]
    server_ip = sys.argv[2]

init_flag = False
hand_init_rot = Quaternion(1, 0, 0, 0)
arm_init_rot = Quaternion(1, 0, 0, 0)
hand_init_pos = (0, 0, 0)
arm_init_pos = (0, 0, 0)
hand_pos = (0.0, 0.0, 0.0)
hand_rot = Quaternion(1, 0, 0, 0)
hand_geo = geometry.Cuboid((0.1, 0.1, 0.25), hand_pos, hand_rot, facecolor="c", edgecolor="#0000FF", alpha=0.3)
arm_pos = (0.0, 0.0, 0.0)
arm_rot = Quaternion(1, 0, 0, 0)
arm_euler = np.zeros(3)
arm_geo = geometry.Cuboid((0.1, 0.1, 0.25), arm_pos, arm_rot, facecolor="m", edgecolor="#FF0000", alpha=0.3)

test_geo = geometry.Cuboid((0.1, 0.1, 0.25), facecolor="y", edgecolor="#0000FF", alpha=0.2)

print("Prepare Plot.")
fig = plt.figure()
gs = gridspec.GridSpec(1, 2, width_ratios=[2, 1])
ax = fig.add_subplot(gs[0], projection='3d', aspect='equal')
ax2 = fig.add_subplot(gs[1])
plt.connect('key_press_event', plt_onkey)
plt.connect('close_event', plt_onclose)

print("Prepare OSC UDP Socket.")
osc_client = ArmCommunicator()

print("Open Data Socket & Command Socket ...")
streamingClient = NatNetClient(local_ip, server_ip)
signal.signal(signal.SIGINT, lambda a, b : streamingClient.close())
streamingClient.rigidBodyListener = receiveNewFrame

print("Opened.\nRun Communication Process Loop.")
print("Enter Ctrl+C to exit.")
print("Or, Press Q key on GUI.")

joint_angles = [0, 0, 0, 0]
arm_euler = [0, 0, 0]
arm2hand_euler = [0, 0, 0]
# =============================== main loop ====================================
try:
    streamingClient.run()
    while(not streamingClient.is_end()):
        # rigid body update
        if init_flag:
            hand_geo.translate(arm_init_rot.inverse.rotate(np.array(hand_pos) - np.array(arm_init_pos)), hand_diff_rot)
            arm_geo.translate(arm_init_rot.inverse.rotate(np.array(arm_pos) - np.array(arm_init_pos)), arm_diff_rot)
        # ax1 set
        ax.set_xlim(-0.5, 0.5)
        ax.set_ylim(-0.5, 0.5)
        ax.set_zlim(-0.5, 0.5)
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")
        ax.add_collection3d(hand_geo.poly())
        ax.add_collection3d(arm_geo.poly())
        ax.add_collection3d(test_geo.poly())
        # ax2 set
        ax2.axis("off")
        ax2.text(0.1, 0.80, "arm : (%5.1f, %5.1f, %5.1f)" % (arm_euler[0], arm_euler[1], arm_euler[2]), 
                backgroundcolor='#FFFFFF', size=10)
        ax2.text(0.1, 0.70, "a2h : (%5.1f, %5.1f, %5.1f)" % (arm2hand_euler[0], arm2hand_euler[1], arm2hand_euler[2]), 
                backgroundcolor='#FFFFFF', size=10)
        # update drawing
        plt.draw()
        plt.pause(1 / VIEW_FPS)
        ax.cla()
        ax2.cla()
finally:
    streamingClient.close()
    osc_client.close()
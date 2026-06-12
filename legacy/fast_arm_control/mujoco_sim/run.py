import time
import math
import numpy as np
import mujoco
import mujoco.viewer
from typing import List
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import UDPClient
from pythonosc.osc_message_builder import OscMessageBuilder
import threading

paused = False
end_flag = False

class JointCommandReceiver:
    def __init__(self, ip="127.0.0.1", port=5555, address="/armR"):
        self.joint_angles = (0.0, 0.0, 0.0, 0.0)
        self.joint_angles_lock = threading.Lock()
        self.dispatcher = Dispatcher()
        self.dispatcher.map(address, self._recv)
        self.server = ThreadingOSCUDPServer(
            (ip, port), self.dispatcher)
        self.osc_thread = threading.Thread(target=self.server.serve_forever)
        self.osc_thread.start()
        self.new_recv = False
    
    def _recv(self, address: str, *data: List[float]):
        with self.joint_angles_lock:
            self.new_recv = True
            self.joint_angles = tuple(data)
    
    def close(self):
        self.server.shutdown()
        self.osc_thread.join()
    
    def get_data(self):
        with self.joint_angles_lock:
            self.new_recv = False
            return self.joint_angles

class ArmStatus:
    def __init__(self, joint_angles, tip_pos):
        self.joint_angles = joint_angles
        self.tip_pos = tip_pos
    
    def build_osc_msg(self, addr="/"):
        if(addr == "/"): addr = ""
        joint_angle_addr = addr + "/joint_angles"
        tip_pos_addr = addr + "/tip_pos"
        # joint angles msg
        msg_builder = OscMessageBuilder(address=joint_angle_addr)
        for j in self.joint_angles:
            msg_builder.add_arg(j)
        joint_angle_msg = msg_builder.build()
        # tip pos msg
        msg_builder = OscMessageBuilder(address=tip_pos_addr)
        for p in self.tip_pos:
            msg_builder.add_arg(p)
        tip_pos_msg = msg_builder.build()
        return joint_angle_msg, tip_pos_msg

class ArmStatusSender:
    def __init__(self, ip = "127.0.0.1", port = 5556):
        self.end_flag = False
        self.osc_client = UDPClient(ip, port)
        self.current_directive = None
        self.osc_send_thread = threading.Thread(target=self._osc_send_thread_process)
        self.osc_send_thread.start()
    
    def join(self):
        self.osc_send_thread.join()
    
    def close(self):
        self.end_flag = True
        self.join()
    
    def _osc_send_thread_process(self):
        while(not self.end_flag):
            with self.directive_lock:
                if(self.current_directive is not None):
                    self._send(self.current_directive)
            time.sleep(self.cycle_time)
        print("OSC send thread is closed.")
    
    def send(self, joint_angles, tip_pos, addr="/"):
        msgs = ArmStatus(joint_angles, tip_pos).build_osc_msg(addr)
        for m in msgs:
            self.osc_client.send(m)

def command_joint_angle(model, data):
    global osc_server
    if(not osc_server.new_recv): return
    joint_angles = osc_server.get_data()
    for i in range(4):
        data.ctrl[i] = joint_angles[i] * math.pi / 180

def get_states(model, data):
    print(f"QPos : {data.qpos}")
    print(f"Tip: {data.site_xpos[0]}")
    pass

# MujocoのGUIでのキー入力に対するコールバック
def key_callback(keycode):
    if(chr(keycode) == ' '):
        global paused
        paused = not paused
    if(chr(keycode) == 'Q' or keycode == 256):
        global end_flag
        end_flag = True

if __name__ == '__main__':
    global osc_server
    try:
        osc_server = JointCommandReceiver()
        # Run MuJoCo
        m = mujoco.MjModel.from_xml_path('./scene.xml')
        d = mujoco.MjData(m)
        # Set home keyframe
        d.qpos = m.key_qpos
        d.ctrl = m.key_ctrl
        with mujoco.viewer.launch_passive(m, d, key_callback=key_callback) as viewer:
            start = time.time()
            while viewer.is_running():
                step_start = time.time()
                if(not paused): 
                    # 1 step 進める
                    get_states(m, d)
                    command_joint_angle(m, d)
                    mujoco.mj_step(m, d)
                    # GUIからの入力を受け付ける
                    viewer.sync()
                # end_flagがたったら終了
                if(end_flag): break
                # 1ループの時間を調整する
                time_until_next_step = m.opt.timestep - (time.time() - step_start)
                if(time_until_next_step > 0):
                    time.sleep(time_until_next_step)
    finally:
        osc_server.close()

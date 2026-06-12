# OSCでArmの関節角を送信
# OSC Clientはスレッドで回す

import time
from pythonosc import osc_message_builder
from pythonosc import udp_client
import threading

# アームへの指令を表すクラス
class ArmDirective:
    def __init__(self, addr: str = "/", joint_angles: tuple = (0.0, 0.0, 0.0, 0.0)):
        self.address = addr
        self.joint_angles = joint_angles

# アームとの通信スレッドを回すクラス
class ArmCommunicator:
    def __init__(self, ip = "127.0.0.1", port = 5555, fps = 240.0, 
                 init_joint_angles = (0.0, 0.0, 0.0, 0.0), allow_angle_dif: float = 300):
        self.end_flag = False
        self.cycle_time = 1 / fps
        self.osc_client = udp_client.UDPClient(ip, port)
        self.current_directive = None
        self.directive_lock = threading.Lock()
        self.previous_joint_angles = init_joint_angles
        self.allow_angle_dif = allow_angle_dif
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
    
    def _send(self, directive: ArmDirective = ArmDirective()) -> None:
        # joint_angles : base yaw, base pitch, elbow yaw, hand pitch
        msg_builder = osc_message_builder.OscMessageBuilder(address=directive.address)
        for j in directive.joint_angles:
            msg_builder.add_arg(j)
        msg = msg_builder.build()
        self.osc_client.send(msg)
        self.previous_joint_angles = directive.joint_angles
    
    def update_directive(self, addr: str, joint_angles: tuple) -> None:
        with self.directive_lock:
            # 角度変化が急な場合は無視する
            for i in range(len(self.previous_joint_angles)):
                angle_dif = joint_angles[i] - self.previous_joint_angles[i]
                if(abs(angle_dif) > self.allow_angle_dif):
                    print(f"!!! Danger !!! Too much change in joint angle ({angle_dif}).")
                    return
            self.current_directive = ArmDirective(addr, joint_angles)
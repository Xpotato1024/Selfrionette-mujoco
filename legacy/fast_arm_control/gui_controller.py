import tkinter as tk
import numpy as np
import math
from kinematics import FastArmKinematics
from mocap_to_joint.arm_communicator import ArmCommunicator
from ik_controller import IKController
import threading
import time

FPS = 30

class Application(tk.Frame):
    def __init__(self, master, fps):
        super().__init__(master=master)
        self.master.title("IK Controller")
        self.master.geometry("480x480")
        self.master.protocol("WM_DELETE_WINDOW", self._close_window)
        # スクロールバーの表示
        self.pose_setting_frame = tk.LabelFrame(self.master, text = "Tip Pose (x, y, z, theta)", 
                                                labelanchor="nw")
        self.tip_input = [tk.DoubleVar(self.master, 0.0) for i in range(4)]
        self.tip_input[2].set(-0.62)
        self.tip_pos_scales = [
            tk.Scale(self.pose_setting_frame, orient = tk.HORIZONTAL, 
                     length = 300, width = 20, sliderlength = 20, 
                     from_ = -1, to = 1,
                     resolution = 0.001, tickinterval = 0.2, 
                     variable = self.tip_input[i]) 
            for i in range(3)]
        self.tip_pos_scales.append(
            tk.Scale(self.pose_setting_frame, orient = tk.HORIZONTAL, 
                     length = 300, width = 20, sliderlength = 20, 
                     from_ = -180, to = 180,
                     resolution = 0.1, tickinterval = 45, 
                     variable = self.tip_input[3]))
        for s in self.tip_pos_scales: s.pack()
        self.pose_setting_frame.pack()
        # IKの解の表示
        self.ik_result_frame = tk.LabelFrame(self.master, text = "IK Result", 
                                             labelanchor = "nw")
        self.ik_result_str = [tk.StringVar(self.master, "None") for i in range(4)]
        self.ik_result_labels = [tk.Label(self.ik_result_frame, 
                                          textvariable=self.ik_result_str[i], 
                                          padx = 5, pady = 5, font = ("Times", 20))
                                 for i in range(4)]
        for s in self.ik_result_labels: s.pack()
        self.ik_result_frame.pack()
        # 運動学
        self.kinematics = FastArmKinematics(0.338, 0.284, [0.15, 0.62], q2_offset=True)
        self.controller = IKController(self.kinematics, init_pose=None, init_angle=np.array((0.0, 0.0, 0.0, 0.0)))
        self.controller.set_joint_angle_limit(np.array([[-math.pi, math.pi], [-math.pi, math.pi], 
                                                        [-math.pi, math.pi], [-math.pi, math.pi]]))
        self.controller.set_joint_speed_limit(np.array([3.0, 3.0, 3.0, 3.0]), fps)     # rad/s
        # OSC
        self.fps = fps
        self.osc = ArmCommunicator(fps = fps)
        self.update_thread = threading.Thread(target = self._update, daemon = True)
        self.update_thread.start()

    def _close_window(self):
        self.osc.close()
        self.master.destroy()
    
    def _update(self):
        while(True):
            ik_input = np.array([self.tip_input[i].get() for i in range(4)])
            ik_input[3] *= math.pi / 180.0
            #ik_output = self.kinematics.inverse(ik_input)
            ik_output = self.controller.output(ik_input)
            # Output
            ik_output *= 180.0 / math.pi
            for i in range(4):
                self.ik_result_str[i].set(
                    "Q%2d : % 5.1f [deg]" % (i + 1, ik_output[i])
                )
            self.osc.update_directive("/armR", ik_output)
            time.sleep(1.0 / self.fps)

if __name__ == "__main__":
    root = tk.Tk()
    app = Application(root, FPS)
    app.mainloop()
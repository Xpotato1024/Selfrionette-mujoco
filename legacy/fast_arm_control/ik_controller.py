from kinematics import FastArmKinematics
import math
import numpy as np

class IKController:
    def __init__(self, kinematics: FastArmKinematics, init_pose: np.ndarray | None = None, 
                 init_angle: np.ndarray | None = np.array([0.0, 0.0, 0.0, 0.0]), 
                 input_offset_yaw: float = 0.0):
        self.kinematics = kinematics
        self.pre_joint_angles = init_angle
        self.input_offset_yaw = input_offset_yaw
        c = math.cos(self.input_offset_yaw)
        s = math.sin(self.input_offset_yaw)
        self.input_offset_rot = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        if(init_pose is not None):
            self.pre_joint_angles = kinematics.inverse(self.input_offset_rot @ init_pose)
        self.joint_angle_limits = None
        self.joint_speed_limits = None
        self.fps = None
    
    def set_joint_angle_limit(self, limit: np.ndarray):
        self.joint_angle_limits = limit

    def set_joint_speed_limit(self, limit: np.ndarray, fps: float):
        self.joint_speed_limits = limit
        self.fps = fps
    
    def output(self, tip_pos: np.ndarray, nv: np.ndarray | None = None) -> np.ndarray:
        _tip_pos = None
        _nv = None
        if(nv is None):
            _tip_pos = np.hstack([self.input_offset_rot @ tip_pos[0:3], 
                                  tip_pos[3] + self.input_offset_yaw])
        else:
            _tip_pos = self.input_offset_rot @ tip_pos
            _nv = self.input_offset_rot @ nv
        joint_angles = self.kinematics.inverse(_tip_pos, _nv, self.pre_joint_angles)
        return self.angle_to_output(joint_angles)
    
    def angle_to_output(self, joint_angles: np.ndarray) -> np.ndarray:
        if(self.joint_angle_limits is not None):
            # 関節角制限
            for i in range(len(joint_angles)):
                joint_angles[i] = max(self.joint_angle_limits[i][0], 
                                      min(joint_angles[i], 
                                          self.joint_angle_limits[i][1]))
        if(self.joint_speed_limits is not None):
            # 関節速度制限
            joint_dif = joint_angles - self.pre_joint_angles
            for i in range(len(joint_dif)):
                if(abs(joint_dif[i]) < self.joint_speed_limits[i] / self.fps):
                    continue
                sign = 1 if(joint_dif[i] > 0) else -1
                joint_angles[i] = sign * self.joint_speed_limits[i] / self.fps + self.pre_joint_angles[i]
        self.pre_joint_angles = joint_angles.copy()
        return joint_angles

    def joint_angles(self) -> np.ndarray:
        return self.pre_joint_angles
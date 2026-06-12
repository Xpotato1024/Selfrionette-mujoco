import numpy as np
from scipy.spatial.transform import Rotation
import math
from typing import Tuple

#
# <運動学モデルと座標軸>
#
#         |<---l1--->|<----l2---->|
# |       |          |            |
# |-<|>---◎---<|>---[]-----------*
# |
#
#  z
#  ↑
# (x) → x
# y
#
# <リンク長>
# 2023/11/21
# l1 = 338, l2 = 284(リンク先端まで)
#

class FastArmKinematics:
    def __init__(self, link1_m: float, link2_m: float, range: None | Tuple[float, float] = None, 
                 axis_flip: bool = False, q2_offset: bool = False):
        self.l1 = link1_m
        self.l2 = link2_m
        self.range = range
        self.axis_flip = axis_flip  # oFの関節角は軸に対し逆ねじの向きを正としているので、反転させる NOTE: モータ換装したので違うかも
        self.q2_offset = q2_offset  # oFでは肩の第二関節に+90[deg]オフセットあり
        
    def forward(self, joint_angles: np.ndarray) -> np.ndarray:
        """順運動学
        Args:
            joint_angles (np.ndarray): 関節角(rad x 4)
        Returns:
            np.ndarray: 手先姿勢(x, y, z, 肘の仰角)
        """
        j = joint_angles.copy()
        if(self.q2_offset):
            j[1] -= math.pi / 2.0
        if(self.axis_flip):
            j *= -1
        ee_pose = FastArmKinematics.solve_FK(j, self.l1, self.l2)
        return ee_pose
    
    def inverse(self, tip_pos: np.ndarray, nv: np.ndarray | None = None, neighbor_angles: None | np.ndarray = None) -> np.ndarray:
        """逆運動学
        Args:
            tip_pos (np.ndarray): 手先位置
            nv (np.ndarray): 腕平面の法線ベクトル
            neighbor_angles (np.ndarray): Optional 参照関節角(rad x 4)、なるべくこれに近い解を求める
        Returns:
            np.ndarray: 関節角度(rad x 4)
        """
        joint_angles = None
        if(nv is None):
            joint_angles = FastArmKinematics.solve_IK(tip_pos, self.l1, self.l2, self.range)
        else:
            joint_angles = FastArmKinematics.solve_IK_with_nv(tip_pos, nv, self.l1, self.l2, self.range)
        if(self.axis_flip):
            joint_angles *= -1
        if(self.q2_offset):
            joint_angles[1] -= math.pi / 2.0
            if(joint_angles[1] > math.pi): 
                joint_angles[1] -= math.pi * 2.0
        if(neighbor_angles is None):
            return joint_angles
        # 最も近い解を選ぶ
        ## 参照関節角がどの範囲か調べる。0: -pi ~ pi, n: -pi + 2n * pi ~ pi + 2n * pi とか
        neighbor_angle_range = (neighbor_angles // math.pi).astype(np.int64)
        for i in range(len(neighbor_angle_range)):
            if(neighbor_angle_range[i] < 0): neighbor_angle_range[i] += 1
        ## 解の候補を出す
        candidates = []
        candidates.append(joint_angles + neighbor_angle_range * 2.0 * math.pi)
        another_angles = np.hstack([
            FastArmKinematics.another_sholder_joint_angles(joint_angles[0:3], self.q2_offset), 
            joint_angles[3]])
        candidates.append(another_angles + neighbor_angle_range * 2.0 * math.pi)
        ## 候補の中から最も近い解を選ぶ
        min_err = 1e128
        for c in candidates:
            for i in range(len(c)):
                err = neighbor_angles[i] - c[i]
                if(err > math.pi):
                    c[i] += math.pi * 2.0
                elif(err < -math.pi):
                    c[i] -= math.pi * 2.0
            err = neighbor_angles - c
            err_sum = np.sum(np.abs(err))
            if(err_sum < min_err):
                min_err = err_sum
                joint_angles = c
        return joint_angles
    
    @classmethod
    def another_sholder_joint_angles(cls, angles: np.ndarray, q2_offset: bool = False) -> np.ndarray:
        """同値な肩の回転変換を表す別の関節角度を計算する
        Args:
            r (np.ndarray): 肩関節角度
        Returns:
            np.ndarray: 同値な変換となる別の肩関節角度
        Note:
            solve_IK()が思ってたのとは違う解を出した時につかう
        """
        rx1, ry, rx2 = angles
        rx1 += math.pi
        if(rx1 > math.pi): rx1 -= math.pi * 2.0
        if(q2_offset):
            ry = math.pi - ry
            if(ry > math.pi): ry -= math.pi * 2.0
        else:
            ry *= -1
        rx2 += math.pi
        if(rx2 > math.pi): rx2 -= math.pi * 2.0
        return np.array([rx1, ry, rx2])

    @classmethod
    def parse_sholder_rot(cls, r: np.ndarray) -> np.ndarray:
        """肩関節(3DoF)の回転行列を各関節角度[rad]へ変換する
        Args:
            r (np.ndarray): 肩関節の回転変換を表す行列(3x3 matrix)
        Returns:
            np.ndarray: 関節角[rad]によってなる配列 (3要素)
        Note:
            基本は回転行列 -> XYXオイラー角の変換処理と同じ
            特異点周りを自分でいじりたいため実装
        """
        if(r[0, 0] > 1 - 1e-6):
            print("sholder rot is specific pose 1")
            return np.array([0.0, 0.0, math.atan2(r[2, 1], r[1, 1])])       # 特異姿勢1
        elif(r[0, 0] < -1 + 1e-6):
            print("sholder rot is specific pose 1")
            return np.array([0.0, math.pi, math.atan2(r[2, 1], r[1, 1])])   # 特異姿勢2
        rx1 = math.atan2(r[1, 0], -r[2, 0])
        rx2 = math.atan2(r[0, 1], r[0, 2])
        ry = math.acos(r[0, 0])
        return np.array([rx1, ry, rx2])

    @classmethod
    def solve_IK(cls, ee_pose: np.ndarray, l1: float, l2: float, 
                 range: None | Tuple[float, float] = None) -> np.ndarray:
        """高速マニピュレータの逆運動学
        Args:
            ee_pose (np.ndarray): 手先位置と肘の仰角によってなる1次元配列 (x, y, z, theta)
            l1 (float): 上腕リンクの長さ
            l2 (float): 前腕リンクの長さ
            range(Tuple(float, float)): Optional, 肩から手先までの距離の制限範囲
        Raises:
            ValueError: 作業空間外の手先位置を渡された場合に発生
        Returns:
            np.ndarray: 各関節角度の配列 (q1, q2, q3, q4)
        """
        ## 腕平面の法線ベクトルを求める
        x, y, z, t = ee_pose
        r2 = x**2 + y**2 + z**2
        r = math.sqrt(r2)
        nx = np.array([0.0, 0.0, 1.0])
        a = 0.0
        if(r > 1e-9):
            nx = np.array([x, y, z]) / r        # 肩 -> 手先 方向の単位ベクトル
            a = math.atan2(x, -z)
        nv_ref = -np.array([math.cos(a), 0.0, math.sin(a)])  # 基準平面の法線ベクトル
        # 肩 -> 手先方向のベクトルを軸に法線ベクトルをt回転させる
        nv = rodrigues_rot_matrix(angle = t, axis = nx) @ nv_ref
        return FastArmKinematics.solve_IK_with_nv(ee_pose[0:3], nv, l1, l2, range)
    
    @classmethod
    def solve_IK_with_nv(cls, ee_pos: np.ndarray, nv: np.ndarray, l1: float, l2: float, 
                         range: None | Tuple[float, float] = None) -> np.ndarray:
        """高速マニピュレータの逆運動学 v2
        Args:
            ee_pos (np.ndarray): 手先位置 (x, y, z)
            nv (np.ndarray):　腕平面の法線ベクトル
            l1 (float): 上腕リンクの長さ
            l2 (float): 前腕リンクの長さ
            range(Tuple(float, float)): Optional, 肩から手先までの距離の制限範囲
        Raises:
            ValueError: 作業空間外の手先位置を渡された場合に発生
        Returns:
            np.ndarray: 各関節角度の配列 (q1, q2, q3, q4)
        """
        x, y, z = ee_pos
        r2 = x**2 + y**2 + z**2
        r = math.sqrt(r2)
        nx = np.array([0.0, 0.0, 1.0])
        if(r > 0):
            nx = np.array([x, y, z]) / r    # 肩 -> 手先 方向の単位ベクトル
        # 1. 肘の角度を求める
        if(range is None):
            if(r2 > (l1 + l2)**2 - 1e-9):
                raise ValueError(f"given pos {ee_pos} is out of the arm's range.")
        else:
            # 手先位置をアームの制限範囲内に修正
            range_min, range_max = range
            if(r < range_min):
                r = range_min
                r2 = range_min**2
            if(r > range_max):
                r = range_max
                r2 = range_max**2
        elbow_angle = math.acos((r2 - l1**2 - l2**2) / 2.0 / l1 / l2)
        delta = math.acos((r2 + l1**2 - l2**2) / 2.0 / l1 / r)
        ## 2. 腕平面の法線ベクトルを求める
        ez = nv - np.dot(nv, nx) * nx
        ez_norm = np.linalg.norm(ez)
        if(ez_norm < 1e-12):
            nv = np.array([0., 1., 0.])
            ez = nv - np.dot(nv, nx) * nx
            ez_norm = np.linalg.norm(ez)
        ez /= -ez_norm          # 腕平面の法線ベクトル
        ## 3. 肩の回転行列を求める
        ny = np.cross(ez, nx)
        ex = nx * math.cos(delta) - ny * math.sin(delta)
        ey = nx * math.sin(delta) + ny * math.cos(delta)
        rot_sholder = np.stack([ex, ey, ez], -1)
        # 4. 肩の回転をオイラー角へ変換
        sholder_q = FastArmKinematics.parse_sholder_rot(rot_sholder)
        return np.array([sholder_q[0], sholder_q[1], sholder_q[2], elbow_angle])

    @classmethod
    def solve_FK(cls, joint_angles: np.ndarray, l1: float, l2: float) -> np.ndarray:
        """高速マニピュレータの順運動学
        Args:
            joint_angles (np.ndarray): 関節角度
            l1 (float): 上腕リンクの長さ
            l2 (float): 前腕リンクの長さ
        Returns:
            np.ndarray: 手先位置と肘の仰角からなる配列
        """
        q1, q2, q3, q4 = joint_angles
        sholder_rot = Rotation.from_euler('xyx', [q3, q2, q1])
        elbow_rot = Rotation.from_euler('z', q4)
        upper_link = np.array([l1, 0.0, 0.0])
        fore_link = np.array([l2, 0.0, 0.0])
        el_pos = sholder_rot.apply(upper_link)
        ee_pos = sholder_rot.apply(upper_link + elbow_rot.apply(fore_link))
        # 肘の仰角を求める
        x, y, z = ee_pos
        n0 = np.array([-y, x, 0])       # 基準平面の法線ベクトル(z軸を含む平面)
        n1 = np.cross(ee_pos, el_pos)   # 腕平面の法線ベクトル
        cos_t = np.dot(n0, n1) / np.linalg.norm(n0) / np.linalg.norm(n1)
        cos_t = max(-1, min(cos_t, 1))  # たまに-1 ~ 1を微小に逸脱するので制限
        t = np.sign(n1[2]) * math.acos(cos_t)
        return np.array([x, y, z, t])

if __name__ == '__main__':
    import sys
    L1 = 0.338
    L2 = 0.27
    AXIS_FLIP = True
    Q2_OFFSET = True
    if(len(sys.argv) < 5):
        print(f"require 4 parameters. \nusage: python {sys.argv[0]} x y z theta")
        exit(1)
    fak = FastArmKinematics(L1, L2, axis_flip=AXIS_FLIP, q2_offset=Q2_OFFSET)
    x, y, z, t = tuple(map(float, sys.argv[1:5]))
    print(f"End Effector Pose : ({x}, {y}, {z} {t})")
    joints = fak.inverse(np.array((x, y, z)), np.array((-0.1, -0.1, 0.1))/math.sqrt(0.03))
    print(f"IK Result: {joints}")
    ee_pos = fak.forward(joints)
    print(f"FK Result: {ee_pos}")
    
    print(" ==================== ")
    print("another solution")
    joints[0:3] = FastArmKinematics.another_sholder_joint_angles(joints[0:3], Q2_OFFSET)
    print(f"IK Result: {joints}")
    ee_pos = fak.forward(joints)
    print(f"FK Result: {ee_pos}\n")

def rodrigues_rot_matrix(angle: float, axis: np.ndarray):
    c = math.cos(angle)
    s = math.sin(angle)
    n = axis
    return np.array([
        [           n[0]**2 * (1 - c) + c, n[0] * n[1] * (1 - c) - n[2] * s, n[0] * n[2] * (1 - c) + n[1] * s], 
        [n[0] * n[1] * (1 - c) + n[2] * s,            n[1]**2 * (1 - c) + c, n[1] * n[2] * (1 - c) - n[0] * s], 
        [n[0] * n[2] * (1 - c) - n[1] * s, n[1] * n[2] * (1 - c) + n[0] * s,            n[2]**2 * (1 - c) + c]])

def rodrigues_rot(v: np.ndarray, angle: float, axis: np.ndarray):
    return rodrigues_rot_matrix(angle, axis) @ v
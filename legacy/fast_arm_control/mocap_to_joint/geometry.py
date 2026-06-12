import math
from pyquaternion import Quaternion
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# Matplotlibに描画する用の直方体クラス
class Cuboid:
  def __init__(self, size = (1.0, 1.0, 1.0), position = np.zeros(3), rotation = Quaternion(1, 0, 0, 0), 
               facecolor="white", edgecolor="black", alpha=1.0, linewidth=1.0):
    self.ps = np.array([[-1, -1, -1],
                        [1, -1, -1 ],
                        [1, 1, -1],
                        [-1, 1, -1],
                        [-1, -1, 1],
                        [1, -1, 1 ],
                        [1, 1, 1],
                        [-1, 1, 1]], dtype=np.float32)
    self.ps[:, 0] *= size[0] / 2.0
    self.ps[:, 1] *= size[1] / 2.0
    self.ps[:, 2] *= size[2] / 2.0
    self.pos = position
    self.rot = rotation
    self.face_clr = facecolor
    self.edge_clr = edgecolor
    self.alpha = alpha
    self.linewidth = linewidth
    return
  
  def position(self, position):
    self.pos = position
  
  def rotation(self, rotation):
    self.rot = rotation
  
  def translate(self, position, rotation):
    self.position(position)
    self.rotation(rotation)
  
  def poly(self):
    ps = np.zeros(self.ps.shape)
    for i in range(self.ps.shape[0]):
      ps[i] = self.rot.rotate(self.ps[i])
    ps += self.pos
    #ps = np.dot(self.ps, self.rot.T) + self.pos
    verts = [[ps[0], ps[1], ps[2], ps[3]], 
            [ps[4], ps[5], ps[6], ps[7]], 
            [ps[0], ps[1], ps[5], ps[4]], 
            [ps[2], ps[3], ps[7], ps[6]], 
            [ps[1], ps[2], ps[6], ps[5]], 
            [ps[4], ps[7], ps[3], ps[0]]]
    return Poly3DCollection(verts, facecolors=self.face_clr, 
                            linewidths=self.linewidth, edgecolors=self.edge_clr, 
                            alpha=self.alpha)


# Matplotlibに描画する用の立方体クラス
class Cube(Cuboid):
  def __init__(self, size = 1.0, position = np.zeros(3), rotation = np.identity(3), 
               facecolor="white", edgecolor="black", alpha=1.0, linewidth=1.0):
    super().__init__((size, size, size), position, rotation, facecolor, edgecolor, alpha, linewidth)

def rotation_matrix(r, p, y):
  rot_x = np.array([[ 1,           0,            0],
                    [ 0, math.cos(r), -math.sin(r)],
                    [ 0, math.sin(r),  math.cos(r)]])

  rot_y = np.array([[ math.cos(p), 0,  math.sin(p)],
                    [           0, 1,            0],
                    [-math.sin(p), 0, math.cos(p)]])

  rot_z = np.array([[ math.cos(y), -math.sin(y), 0],
                    [ math.sin(y),  math.cos(y), 0],
                    [           0,            0, 1]])
  return rot_z.dot(rot_y.dot(rot_x))
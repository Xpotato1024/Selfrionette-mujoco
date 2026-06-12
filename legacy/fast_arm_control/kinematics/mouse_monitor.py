from pynput import mouse
import numpy as np

class MouseMonitor:
    def __init__(self, gain = np.array([1.0, 1.0, 1.0])):
        self.move_initialized = False
        self.pre_mx = 0
        self.pre_my = 0
        self.pos = np.array([0, 0, 0])
        self.gain = gain
        self.listener = mouse.Listener(on_move=self._on_move, 
                                       on_scroll=self._on_scroll)
    
    def __del__(self):
        self.listener.stop()
    
    def _on_move(self, x, y):
        if(not self.move_initialized):
            self.pre_mx = x
            self.pre_my = y
            self.move_initialized = True
        self.pos[0] += x - self.pre_mx
        self.pos[1] += y - self.pre_my
        self.pre_mx, self.pre_my = x, y
    
    def _on_scroll(self, x, y, dx, dy):
        self.pos[2] += dy
    
    def start(self):
        self.listener.start()
    
    def stop(self):
        self.listener.stop()
    
    def get(self):
        return self.pos * self.gain

if __name__ == "__main__":
    import time
    mm = MouseMonitor(np.array([0.1, 0.1, 10.0]))
    mm.start()
    for i in range(200):
        print(mm.get())
        time.sleep(0.1)
    mm.stop()
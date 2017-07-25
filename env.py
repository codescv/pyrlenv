from PIL import ImageGrab
import win32process
import win32gui
import sys
import time
import win32con
import itertools
import threading
from mss import mss, tools
import numpy as np
import cv2


class ImageCaptureThread(threading.Thread):
    def __init__(self, env, hwnd, cond_first_img, fps=25.0):
        super().__init__()
        self.__env = env
        self.__hwnd = hwnd
        self.__cond_first_img = cond_first_img
        self.__stop = False
        self.__interval = 1.0 / fps

    def stop(self):
        self.__stop = True

    def run(self):
        screen = mss()
        n_frames = 0
        time_start = time.time()
        while not self.__stop:
            time_frame_start = time.time()
            bbox = win32gui.GetWindowRect(self.__hwnd)
            left, top, right, bottom = bbox
            img = screen.grab({'top': top, 'left': left, 'width': right-left, 'height': bottom-top})
            self.__cond_first_img.acquire()
            self.__env.set_image(np.array(img))
            self.__cond_first_img.notifyAll()
            self.__cond_first_img.release()
            sleep_time = self.__interval - (time.time() - time_frame_start)
            delta = 0.00001
            while sleep_time > 0:
                time.sleep(delta)
                sleep_time = self.__interval - (time.time() - time_frame_start)
            n_frames += 1
            if n_frames == 100:
                print('fps: ', n_frames / (time.time() - time_start))
                n_frames = 0
                time_start = time.time()


class RLEnv(object):
    def __init__(self,
                 program_cmdline, # full command line to start program
                 window_size=(200, 200)):
        self.__cmdline = program_cmdline
        self.__window_size = window_size
        self.__hwnd = None
        self.__img = None
        self.__capture_thread = None

    def reset(self):
        if not self.__hwnd:
            self._start()

    def set_image(self, img):
        self.__img = img

    def step(self):
        return self.__img

    def stop(self):
        if self.__capture_thread:
            self.__capture_thread.stop()
            self.__capture_thread.join()

    def _start(self):
        assert self.__hwnd is None

        startObj = win32process.STARTUPINFO()
        # hProcess, hThread, pid, tid
        result = win32process.CreateProcess(self.__cmdline, None, None, None, 8, 8, None, None, startObj)
        pid = result[2]
        processList = win32process.EnumProcesses()
        if pid not in processList:
            raise Exception('unable to start process: ', self.__cmdline)

        def init_window(hwnd, pid):
            # the pid matches the window, and make sure to get the parent window
            # because some programs will cause other windows(e.g. IMEs) to start
            if pid == win32process.GetWindowThreadProcessId(hwnd)[1] and win32gui.GetParent(hwnd) == 0:
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 0, 0, self.__window_size[0], self.__window_size[1], 0)
                win32gui.SetForegroundWindow(hwnd)
                self.__hwnd = hwnd

        retry = 0
        print('wating for window...')
        while self.__hwnd is None and retry < 10:
            retry += 1
            win32gui.EnumWindows(init_window, pid)
            time.sleep(1)

        if self.__hwnd is None:
            raise Exception('unable to get window: ', self.__cmdline)

        cond_first_img = threading.Condition()
        self.__capture_thread = ImageCaptureThread(env=self, hwnd=self.__hwnd, cond_first_img=cond_first_img)
        self.__capture_thread.start()
        cond_first_img.acquire()
        while self.__img is None:
            cond_first_img.wait()
        cond_first_img.release()


def main():
    env = RLEnv(program_cmdline="C:\\Windows\\system32\\notepad.exe", window_size=(300, 300))
    env.reset()
    img = env.step()
    print('img:', img.shape)
    #tools.to_png(img.rgb, img.size, "d:\\a.png")
    time.sleep(10)
    env.stop()

if __name__ == '__main__':
    main()

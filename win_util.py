import ctypes

def sleep(seconds):
    kernel32 = ctypes.windll.kernel32

    # This sets the priority of the process to realtime--the same priority as the mouse pointer.
    kernel32.SetThreadPriority(kernel32.GetCurrentThread(), 31)
    # This creates a timer. This only needs to be done once.
    timer = kernel32.CreateWaitableTimerA(ctypes.c_void_p(), True, ctypes.c_void_p())
    # The kernel measures in 100 nanosecond intervals, so we must multiply .25 by 10000
    delay = ctypes.c_longlong(int(seconds * 10000))
    kernel32.SetWaitableTimer(timer, ctypes.byref(delay), 0, ctypes.c_void_p(), ctypes.c_void_p(), False)
    kernel32.WaitForSingleObject(timer, 0xffffffff)

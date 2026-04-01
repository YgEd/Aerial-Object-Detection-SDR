from gnuradio import gr
import subprocess
import sys
import numpy as np
import time
import queue
import threading
from packet_construct import PacketConstructor


# class cvBlock(gr.sync_block):
class cvBlock(gr.sync_block):
    def __init__(self):
        gr.sync_block.__init__(
            self,
            name='Aerial Object Detction Block',
            in_sig=None,
            out_sig = [np.byte]
        )

        # define variable for cv subprocess pointer
        self.cv_proc = None
        # declare packetcontructer object
        self.pc = PacketConstructor()
        # message queue to store cv stdout in
        self._q = queue.Queue()
        # packet queue to store cv constructed packets into
        self._pack_q = queue.Queue()
        # Thread that reads the output from cv_proc and stores it in self._q
        self._reader_thread = None
        
    # define thread reading from subprocess
    # takes each line in byte format converts it to string and puts it in queue
    def _add_to_q(self, stream, msg_q, packet_q):
        # read lines until the b'' condition is found
        for line in iter(stream.readline, b''):
            msg_q.put(line)
            packet_q.put(self.pc.build_packet(line))


    def _waitForProcStart(self, timeout:float = 10.0):
        deadline = time.monotonic() + timeout
        # string sender outputs when it is finished spinning up
        target_str = "Sender started"
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            try:
                # .get() command blocks till remaining time
                line = self._q.get(timeout=remaining)
                line = line.decode().strip()
                if target_str in line:
                    return True
            except queue.Empty:
                break
        print("[cvBlock] CV script didn't start correctly")
        return False
    

    def start(self):
        print(f"[cvBlock] Starting CV script...\r",end="", flush=True)
        if self.cv_proc is None and self._reader_thread is None:

            # start subprocess cv script
            self.cv_proc = subprocess.Popen(
            [sys.executable, "sender.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            )

            # start thread to read cv script output and push to queue
            self._reader_thread = threading.Thread(
            target=self._add_to_q,
            args=(self.cv_proc.stdout, self._q, self._pack_q),
            daemon=True
            )
            self._reader_thread.start()

            # Check if cv script has started
            started = self._waitForProcStart()
            if started:
                print(f"[cvBlcok] CV script started successfully!")
            else:
                return False
        else:
            print(f"[cvBlock] Cannot start mutliple instances of CV script")
    
    
        
    def stop(self):
        print("[cvBlock] Stopping cvBlock...\r", end="", flush=True)
        if self.cv_proc is not None:

            # ask the subprocess to stop
            self.cv_proc.terminate()
            try:
                # wait for response
                self.cv_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # if didn't exit cleanly in time force kill
                self.cv_proc.kill()
                # always reap/wait after kill
                self.cv_proc.wait()
            
            # Next we join the reader thread
            self._reader_thread.join(timeout=10)
            if self._reader_thread.is_alive():
                print("[cvBlock] reader thread did not exist cleanly")
            else:
                print("[cvBlock] Exited cleanly, stopped")


    def checkCV(self):
        print(self._q.get())


# TODO: HAVE TO PUT PACKET CONSTRUCTION LOGIC IN HERE TO TAKE UNPACK BYTES AND HAVE PREAMBLE AND ALL THAT


    def work(self, input_items, output_items):


        # code for sending packet

        # output_tiems stores list of np arrays for each output, because this block only has one output we just get the first output
        out = output_items[0]
        # GNU Radio pre-allocates out with a specific length before calling work
        # This is the amount of samples the scheduler is asking your block to produce this call
        n_requested = len(out)

        # check message queue, if its empty return nothing
        if self._pack_q.qsize() == 0:
            return 0
        
        # if there are messages in the queue, send out as many as possible
        n = min(n_requested, self._pack_q.qsize())

        # get n amount of messages from queue and append to out
        for _ in range(n):
            try:
                # put packet in queue
                out.append(self._pack_q.get_nowait())
            except queue.Empty:
                break
        
        # fill remainig with zeros as there may be garbage in there
        if n < n_requested:
            out[n:] = 0




# if __name__ == '__main__':

#     print("starting object detection...")
#     cv = cvBlock()
#     cv.start()

#     while(True):
#         cli_in = input("Press 'o' for output and 'q' to quit: ")
#         if cli_in == 'o':
#             cv.checkCV()
#         if cli_in == 'q':
#             cv.stop()
#             sys.exit(0)
#         time.sleep(2)

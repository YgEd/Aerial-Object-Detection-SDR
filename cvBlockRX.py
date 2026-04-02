from gnuradio import gr
import numpy as np
from packet_construct import PacketConstructor
import subprocess
import sys
import time


class cvBlockRX(gr.sync_block):
    def __init__(self):
        gr.sync_block.__init__(
            self,
            name='CV Receive Block',
            in_sig=[np.byte],
            out_sig = None
        )

        self.bit_buffer = []
        self.state = "SEARCHING"
        self._pc = PacketConstructor()
        self.constructed_bits = []
        self.rx_proc = None


    def start(self):

        if self.rx_proc is None:
            print(f"[cvBLockRX] Starting Receiver GUI")
            self.rx_proc = subprocess.Popen(
                [sys.executable, "receiver_sdr.py"],
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            # give it 5 seconds to boot
            time.sleep(5)
            
    
    def stop(self):
        print(f"[cvBLockRX] Stopping Receiver GUI")
        if self.rx_proc is not None:
            self.rx_proc.terminate()
        
        try:
            self.rx_proc.wait(timeout=10)
        except:
             # if didn't exit cleanly in time force kill
            self.rx_proc.kill()
            # always reap/wait after kill
            self.rx_proc.wait()

        print(f"[cvBLockRX] Stopped Receiver GUI")
    
    def work(self, input_items, output_items):

        bits_in = input_items[0]
        len_sync = len(self._pc.sync_word)
        sync_word = self._pc.sync_word

        for bit in bits_in:
            self.bit_buffer.append(bit)


            # [SEARCHING FOR SYNC WORD STATE]
            if self.state == 'SEARCHING':
                if len(self.bit_buffer) >= len_sync:
                    tail = self.bit_buffer[-len_sync:]
                    if np.array_equal(tail, sync_word):
                        print('[cvBlockRX] sync word found!')
                        # clear bit buffer so the next bits should be payloadlencrc
                        self.bit_buffer = []
                        self.state = 'READ_LENGTH'
                        self.constructed_bits.append(sync_word)


            # [READING PACKET LENGTH STATE]
            elif self.state == 'READ_LENGTH':

                # two bytes/16 bits represent the payload length + 8 bit crc
                if len(self.bit_buffer) >= 24:

                    raw_bits = self.bit_buffer[:16]
                    len_bytes = self._pc.bits_to_bytes(raw_bits)
                    # 8crc is just one byte so when we turn the bits to bytes there's only one elment in the byte array
                    received_crc_bits = self.bit_buffer[16:24]
                    expected_crc_bits = self._pc.crc8(list(len_bytes))

                    if received_crc_bits != expected_crc_bits:
                        print(f"[cvBlockRX] Length CRC FAILED")
                        self.bit_buffer = []
                        self.constructed_bits = []
                        self.state = 'SEARCHING'
                    
                    else:
                        # convert payload length from bytes to int
                        self.payload_len = (len_bytes[0] << 8 | len_bytes[1])
                        print(f"[cvBlockRX] Length CRC Passed! Payload length: {self.payload_len}")
                        self.bit_buffer = []
                        self.constructed_bits.append(raw_bits)
                        self.state = 'READ_PAYLOAD'
                
            
            elif self.state == 'READ_PAYLOAD':

                # ensure there are enough bits in the bit buffer to include payload and payload crc
                # multiply payload_len by 8 because payload_len is an int curently
                if len(self.bit_buffer) >= (self.payload_len * 8) + 16:

                    raw_payload_bits = self.bit_buffer[:(self.payload_len*8)]
                    raw_payload_bytes = self._pc.bits_to_bytes(raw_payload_bits)
                    received_payload_crc_bits = self.bit_buffer[(self.payload_len*8):(self.payload_len*8) + 16]
                    expected_payload_crc_bits = self._pc.crc16(list(raw_payload_bytes))

                    if received_payload_crc_bits != expected_payload_crc_bits:
                        print(f'[cvBlockRX] Payload CRC FAILED')
                        self.bit_buffer = []
                        self.constructed_bits = []
                        self.state = 'SEARCHING'
                    else:
                        print(f'[cvBlockRX] Payload CRC Passed! Message Received: ',end="")
                        self.bit_buffer = []
                        self.constructed_bits.append(raw_payload_bits)

                        # unwhiten message
                        msg = self._pc.whiten(raw_payload_bytes)
                        print(f'[cvBlockRX] received msg: {msg}')
                        self.rx_proc.stdin.write(msg)
                        self.bit_buffer = []
                        self.constructed_bits = []
                        self.state = 'SEARCHING'


        
        return len(input_items)







            





    



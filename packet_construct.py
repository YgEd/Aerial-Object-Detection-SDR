import numpy as np


class PacketConstructor():
    def __init__(self):

        # sync word
        self.sync_word = np.unpackbits(np.array([0x02, 0xb8, 0xdb], dtype=np.uint8)).tolist()
        # preamble
        self.preamble = np.unpackbits(np.array([37,85,85,85,85,85], dtype=np.uint8)).tolist()

    # packs bits and pads to correct size somehting np.pack does not due which could lead to truncated results
    def bits_to_bytes(self, bits):
        bit_array = np.array(bits, dtype=np.uint8)
        pad = (8 - len(bit_array) % 8) % 8
        if pad:
            bit_array = np.append(bit_array, np.zeros(pad, dtype=np.uint8))
        return bytearray(np.packbits(bit_array))


    def whiten(self, data, seed=0x1FF):
        lfsr = seed
        out = []
        for byte in data:
            whitened = 0
            for bit in range(8):
                # XOR data bit with LFSR output
                lfsr_bit = (lfsr >> 0) & 1
                data_bit = (byte >> bit) & 1
                whitened |= ((data_bit ^ lfsr_bit) << bit)
                # Advance LFSR (x^9 + x^5 + 1)
                feedback = ((lfsr >> 0) ^ (lfsr >> 4)) & 1
                lfsr = (lfsr >> 1) | (feedback << 8)
            out.append(whitened)
        return bytearray(out)


    # returns array of bits of the crc'ed bytes
    def crc8(self, data, poly=0x07, init=0x00):
        crc = init
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = ((crc << 1) ^ poly) & 0xFF
                else:
                    crc= (crc << 1) & 0xFF

        return np.unpackbits(np.array([crc], dtype=np.uint8)).tolist()
        


    # returns array of bits of the crc'ed bytes
    def crc16(self, data, poly =0x8005, init=0xFFFF):
        crc = init
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ poly) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF

        return np.unpackbits(np.array([crc >> 8, crc & 0xFF], dtype=np.uint8)).tolist()
    
    def build_packet(self, message: bytes):

        # whiten message
        msg = self.whiten(message)

        # expects bytes as input
        
        # calculate pyload crc 
        # (use crc16 as it is less likely for corrupted data to produce a correct checksum)
        payload_bits = np.unpackbits(msg).tolist()
        payload_crc_bits = self.crc16(msg)
        payload_len = len(msg)
        
        # convert length thats in int to bit array
        payload_len = np.ceil(len(payload_bits) / 8).astype(int)
        payload_len_bytes = np.array([payload_len >> 8, payload_len & 0xFF], dtype=np.uint8)
        payload_len_bits = np.unpackbits(payload_len_bytes).tolist()
        payload_len_crc_bits = self.crc8(payload_len_bytes)

        packet = np.concatenate([
            # Packet architecture
            # [[preamble][sync_word][payload_len][payload_len_crc][payload][payload_crc]]
            self.preamble,
            self.sync_word,
            payload_len_bits,
            payload_len_crc_bits,
            payload_bits,
            payload_crc_bits
        ])
        return packet
    

    def read_payload(self, payload):
        # pack bits
        un_whitened_msg = self.bits_to_bytes(payload)
        # whiten bytes
        msg = self.whiten(un_whitened_msg)

        return msg
    
    



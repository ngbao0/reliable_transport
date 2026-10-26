import argparse
import socket
import sys
import time
from utils import PacketHeader, compute_checksum

def sender(receiver_ip, receiver_port, window_size):
    """TODO: Open socket and send message from sys.stdin."""
    
    def make_packet(pkt_type, seq_num, data=b""):
        header = PacketHeader(type=pkt_type, seq_num=seq_num, length=len(data), checksum=0)
        header.checksum = compute_checksum(header / data)
        return bytes(header / data)

    def verify_checksum(pkt):
        header = PacketHeader(pkt[:16])
        msg = pkt[16: 16 + header.length]
        rcv_checksum = header.checksum
        header.checksum = 0
        return rcv_checksum == compute_checksum(header / msg), header

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0.5)

    data = sys.stdin.buffer.read()
    chunk_size = 1456
    chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
    total_packets = len(chunks)

    s.sendto(make_packet(0, 0), (receiver_ip, receiver_port))
    try:
        s.recvfrom(2048)
    except socket.timeout:
        pass

    base = 1
    next_seq_num = 1
    acked_packets = set()

    while base <= total_packets:
        while next_seq_num < base + window_size and next_seq_num <= total_packets:
            chunk = chunks[next_seq_num - 1]
            s.sendto(make_packet(2, next_seq_num, chunk), (receiver_ip, receiver_port))
            next_seq_num += 1

        try:
            ack_pkt, _ = s.recvfrom(2048)
            is_valid, ack_header = verify_checksum(ack_pkt)
            
            if is_valid and ack_header.type == 3:
                ack_seq = ack_header.seq_num
                if base <= ack_seq < next_seq_num:
                    acked_packets.add(ack_seq)
                while base in acked_packets:
                    acked_packets.remove(base)
                    base += 1
        except socket.timeout:
            for i in range(base, next_seq_num):
                if i not in acked_packets:
                    chunk = chunks[i - 1]
                    s.sendto(make_packet(2, i, chunk), (receiver_ip, receiver_port))

    end_seq = total_packets + 1
    s.sendto(make_packet(1, end_seq), (receiver_ip, receiver_port))
    
    start_time = time.time()
    while time.time() - start_time < 0.5:
        try:
            ack_pkt, _ = s.recvfrom(2048)
            is_valid, ack_header = verify_checksum(ack_pkt)
            if is_valid and ack_header.type == 3:
                break
        except socket.timeout:
            pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("receiver_ip", help="The IP address of the host that receiver is running on")
    parser.add_argument("receiver_port", type=int, help="The port number on which receiver is listening")
    parser.add_argument("window_size", type=int, help="Maximum number of outstanding packets")
    args = parser.parse_args()
    sender(args.receiver_ip, args.receiver_port, args.window_size)

if __name__ == "__main__":
    main()
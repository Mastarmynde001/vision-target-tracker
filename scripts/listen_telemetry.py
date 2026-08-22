#!/usr/bin/env python3
"""Lightweight UDP telemetry listener receiver utility for testing live streams."""

import argparse
import json
import socket
import sys


def parse_args():
    parser = argparse.ArgumentParser(
        description="Live UDP Telemetry Receiver Utility for vision-target-tracker"
    )
    parser.add_argument(
        "--ip",
        type=str,
        default="127.0.0.1",
        help="Local IP address to bind (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5005,
        help="UDP port to listen on (default: 5005)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((args.ip, args.port))
    except OSError as e:
        print(f"Error: Unable to bind to {args.ip}:{args.port} - {e}", file=sys.stderr)
        sys.exit(1)

    print(f"📡 Telemetry Receiver listening on UDP {args.ip}:{args.port}...")
    print("-" * 75)
    print(f"{'FRAME':<8} {'TARGET':<8} {'CENTROID (X,Y)':<18} {'VELOCITY (Vx,Vy)':<20} {'FPS':<8}")
    print("-" * 75)

    packet_count = 0
    try:
        while True:
            data, addr = sock.recvfrom(2048)
            packet_count += 1
            try:
                payload = json.loads(data.decode("utf-8"))
                frame_id = payload.get("frame_id", "-")
                target_id = payload.get("target_id", "-")
                cx = payload.get("centroid_x", 0)
                cy = payload.get("centroid_y", 0)
                vx = payload.get("velocity_x", 0.0)
                vy = payload.get("velocity_y", 0.0)
                fps = payload.get("fps", 0.0)

                centroid_str = f"({cx}, {cy})"
                velocity_str = f"({vx:+.1f}, {vy:+.1f})"

                print(
                    f"{frame_id:<8} {target_id:<8} {centroid_str:<18} {velocity_str:<20} {fps:<8.1f}"
                )
            except json.JSONDecodeError:
                print(f"Warning: Received non-JSON UDP payload from {addr}: {data}")

    except KeyboardInterrupt:
        print("\nStopping telemetry listener.")
    finally:
        sock.close()
        print(f"Receiver closed. Total packets received: {packet_count}")


if __name__ == "__main__":
    main()

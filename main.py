"""CLI entrypoint for vision-target-tracker handling webcam streams, video files, and hardware telemetry streaming."""

import argparse
import sys
import time
import cv2
from tracking_engine import (
    ObjectTracker,
    FPSBenchmark,
    UDPTelemetryBroadcaster,
    SerialTelemetryBroadcaster,
    draw_target_annotations,
    draw_fps_overlay,
    create_side_by_side,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Real-time Vision Target Tracker CLI Stream Parser"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="0",
        help="Input source: camera index (e.g. '0') or path to video file/image",
    )
    parser.add_argument(
        "--hsv-lower",
        type=int,
        nargs=3,
        default=[35, 50, 50],
        metavar=("H", "S", "V"),
        help="Lower HSV threshold values (default: 35 50 50)",
    )
    parser.add_argument(
        "--hsv-upper",
        type=int,
        nargs=3,
        default=[85, 255, 255],
        metavar=("H", "S", "V"),
        help="Upper HSV threshold values (default: 85 255 255)",
    )
    parser.add_argument(
        "--min-area",
        type=float,
        default=500.0,
        help="Minimum target contour area threshold in pixels (default: 500.0)",
    )
    parser.add_argument(
        "--udp-ip",
        type=str,
        default="127.0.0.1",
        help="UDP telemetry target IP host address (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--udp-port",
        type=int,
        default=5005,
        help="UDP telemetry target port number (default: 5005)",
    )
    parser.add_argument(
        "--serial-port",
        type=str,
        default=None,
        help="Serial port path (e.g., /dev/ttyUSB0 or COM3) for microcontroller telemetry",
    )
    parser.add_argument(
        "--baudrate",
        type=int,
        default=115200,
        help="Serial communication baud rate (default: 115200)",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Disable interactive cv2.imshow GUI display window",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Optional maximum number of frames to process before exiting",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save output video (optional)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Determine input source type (webcam index vs file path)
    source = int(args.source) if args.source.isdigit() else args.source

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Error: Could not open video source '{source}'", file=sys.stderr)
        sys.exit(1)

    tracker = ObjectTracker(
        hsv_lower=tuple(args.hsv_lower),
        hsv_upper=tuple(args.hsv_upper),
        min_area=args.min_area,
    )
    benchmark = FPSBenchmark()

    # Initialize Telemetry Broadcasters
    udp_broadcaster = UDPTelemetryBroadcaster(host=args.udp_ip, port=args.udp_port)
    udp_broadcaster.start()

    serial_broadcaster = None
    if args.serial_port:
        serial_broadcaster = SerialTelemetryBroadcaster(
            port=args.serial_port, baudrate=args.baudrate
        )
        serial_broadcaster.start()

    writer = None
    frame_count = 0

    print(f"Starting target tracker on source: {source}")
    print(f"Telemetry broadcasting to UDP {args.udp_ip}:{args.udp_port}")
    if args.serial_port:
        print(f"Telemetry broadcasting to Serial {args.serial_port}@{args.baudrate}")

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame_count += 1
            if args.max_frames and frame_count > args.max_frames:
                break

            timestamp = time.time()

            with benchmark:
                targets = tracker.track(frame, timestamp=timestamp)
                mask = tracker.create_mask(frame)

                annotated = frame.copy()
                for target in targets:
                    annotated = draw_target_annotations(annotated, target)

                annotated = draw_fps_overlay(annotated, benchmark.fps, benchmark.latency_ms)

                # Dispatch telemetry packet for detected primary target
                if targets:
                    primary = targets[0]
                    telemetry_payload = {
                        "timestamp": timestamp,
                        "frame_id": frame_count,
                        "target_id": 1,
                        "centroid_x": primary.centroid[0],
                        "centroid_y": primary.centroid[1],
                        "velocity_x": round(primary.velocity[0], 2),
                        "velocity_y": round(primary.velocity[1], 2),
                        "fps": round(benchmark.fps, 2),
                    }
                    udp_broadcaster.send(telemetry_payload)
                    if serial_broadcaster:
                        serial_broadcaster.send(telemetry_payload)

            if args.output:
                if writer is None:
                    h, w = annotated.shape[:2]
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    writer = cv2.VideoWriter(args.output, fourcc, 30.0, (w, h))
                writer.write(annotated)

            if not args.no_display:
                composite = create_side_by_side(annotated, mask)
                cv2.imshow("Vision Target Tracker", composite)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    finally:
        cap.release()
        if writer:
            writer.release()
        if not args.no_display:
            cv2.destroyAllWindows()

        # Stop Telemetry Broadcasters
        udp_broadcaster.stop()
        if serial_broadcaster:
            serial_broadcaster.stop()

    summary = benchmark.get_summary()
    print("Execution complete.")
    print(f"Total Frames: {summary['total_frames']}")
    print(f"Elapsed Time: {summary['elapsed_sec']}s")
    print(f"Average FPS: {summary['avg_fps']}")
    print(f"Average Latency: {summary['avg_latency_ms']}ms")


if __name__ == "__main__":
    main()
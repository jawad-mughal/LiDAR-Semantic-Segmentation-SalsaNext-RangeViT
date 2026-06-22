import os
import glob
import argparse
import numpy as np
from rosbags.highlevel import AnyReader
from pathlib import Path

# Map PointField.datatype to numpy typecode and sizes
import struct

# datatype constants from sensor_msgs/PointField
PF_INT8 = 1
PF_UINT8 = 2
PF_INT16 = 3
PF_UINT16 = 4
PF_INT32 = 5
PF_UINT32 = 6
PF_FLOAT32 = 7
PF_FLOAT64 = 8

DTYPE_MAP = {
    PF_FLOAT32: ('f4', 'f'),
    PF_FLOAT64: ('f8', 'd'),
    PF_UINT8:   ('u1', 'B'),
    PF_UINT16:  ('u2', 'H'),
    PF_UINT32:  ('u4', 'I'),
    PF_INT8:    ('i1', 'b'),
    PF_INT16:   ('i2', 'h'),
    PF_INT32:   ('i4', 'i'),
}

REMISSION_PREFERRED = ('intensity', 'reflectivity', 'signal')


def fields_to_dtype(fields, is_bigendian, point_step):
    """Build a numpy dtype that matches PointCloud2 layout including padding.
    Ensures dtype.itemsize == point_step.
    """
    dt_entries = []
    offset = 0
    endian = '>' if is_bigendian else '<'
    for f in fields:
        # align to field.offset by inserting padding
        if f.offset > offset:
            pad = f.offset - offset
            dt_entries.append((f'_pad{offset}', f'|V{pad}'))
            offset += pad
        if f.datatype not in DTYPE_MAP:
            raise ValueError(f"Unsupported datatype {f.datatype} for field {f.name}")
        base_code, struct_code = DTYPE_MAP[f.datatype]
        dt_entries.append((f.name, endian + base_code))
        offset += struct.calcsize(struct_code)
    # add trailing padding so total == point_step
    if offset < point_step:
        dt_entries.append((f'_pad_end', f'|V{point_step - offset}'))
    return np.dtype(dt_entries)


def pc2_to_xyzr(msg):
    """Convert PointCloud2 (ROS1/ROS2) to float32 Nx4 [x,y,z,remission]."""
    field_names = [f.name for f in msg.fields]
    for needed in ('x', 'y', 'z'):
        if needed not in field_names:
            raise RuntimeError("PointCloud2 message does not contain x,y,z fields.")

    # Build dtype matching the exact row layout
    dt = fields_to_dtype(msg.fields, msg.is_bigendian, msg.point_step)
    if dt.itemsize != msg.point_step:
        raise ValueError(f"Computed dtype size {dt.itemsize} != point_step {msg.point_step}; field layout mismatch.")

    # Compute number of points
    H, W = int(msg.height), int(msg.width)
    npts = H * W
    if npts == 0:
        return np.zeros((0, 4), dtype=np.float32)

    # Create structured array view over the raw buffer, honoring row_step padding
    pt_size = int(msg.point_step)
    row_step = int(msg.row_step)
    data = memoryview(msg.data)
    if row_step == pt_size * W:
        # Tightly packed, a simple contiguous view works
        arr = np.frombuffer(data, dtype=dt, count=npts)
    else:
        # Row-padded: make a 2D byte view and stride over rows and points
        byte_rows = np.frombuffer(data, dtype=np.uint8).reshape(H, row_step)
        arr = np.ndarray(shape=(H, W), dtype=dt, buffer=byte_rows.data, strides=(row_step, pt_size)).reshape(npts)

    # Extract xyz
    x = np.asarray(arr['x'], dtype=np.float32)
    y = np.asarray(arr['y'], dtype=np.float32)
    z = np.asarray(arr['z'], dtype=np.float32)

    # Choose remission using datatype-aware scaling
    field_map = {f.name: f for f in msg.fields}
    rem = None
    rem_name = None
    for name in REMISSION_PREFERRED:
        if name in field_map:
            rem_name = name
            break
    if rem_name is not None:
        rem = np.asarray(arr[rem_name], dtype=np.float32)
        dtype_code = field_map[rem_name].datatype
        if dtype_code in (PF_UINT8, PF_INT8):
            rem = rem / 255.0
        elif dtype_code in (PF_UINT16, PF_INT16):
            rem = rem / 65535.0
        elif dtype_code in (PF_UINT32, PF_INT32):
            rmax = float(np.nanmax(rem)) if np.isfinite(rem).any() else 1.0
            rem = rem / (rmax if rmax > 0 else 1.0)
        # FLOAT32/FLOAT64: keep as-is; clamp later
    else:
        if 'range' in field_map:
            rem = np.asarray(arr['range'], dtype=np.float32)
            rmax = float(np.nanmax(rem)) if np.isfinite(rem).any() else 1.0
            rem = rem / (rmax if rmax > 0 else 1.0)
        else:
            rem = np.ones_like(x, dtype=np.float32)

    # Final clamp to [0,1]
    rem = np.clip(rem, 0.0, 1.0)

    xyz = np.stack([x, y, z], axis=1)

    # Filter out invalid and padded points:
    # - non-finite coordinates
    # - zero triples (x=y=z=0) which are padding for many LiDARs/ROS drivers
    finite = np.isfinite(xyz).all(axis=1)
    nonzero = ~((x == 0.0) & (y == 0.0) & (z == 0.0))

    # Some Ouster streams use tiny near-zero placeholders; drop very small radii too
    # (threshold 1 mm to be safe)
    small_radius = np.linalg.norm(xyz, axis=1) < 1e-3
    valid = finite & nonzero & (~small_radius)

    out = np.concatenate([xyz[valid], rem[valid, None]], axis=1).astype(np.float32)
    return out


def convert_bags(bag_dir, topic, out_root):
    bag_paths = sorted(Path(bag_dir).glob('*.bag'))
    if not bag_paths:
        raise FileNotFoundError(f"No .bag found in {bag_dir}")

    sequences_root = os.path.join(out_root, 'sequences')
    os.makedirs(sequences_root, exist_ok=True)

    for seq_idx, bag_path in enumerate(bag_paths):
        seq = f"{seq_idx:02d}"
        seq_dir = os.path.join(sequences_root, seq)
        velodyne_dir = os.path.join(seq_dir, 'velodyne')
        os.makedirs(velodyne_dir, exist_ok=True)
        times_path = os.path.join(seq_dir, 'times.txt')
        print(f"Reading {bag_path.name} -> sequence {seq}")

        with AnyReader([bag_path]) as reader:
            # Find matching topic connections
            connections = [c for c in reader.connections if c.topic == topic]
            if not connections:
                # Help the user by listing available topics
                avail = sorted({c.topic for c in reader.connections})
                raise RuntimeError(f"Topic '{topic}' not found in {bag_path}. Available topics: {avail}")

            # Gather and sort messages by timestamp across all connections
            messages = []
            for conn in connections:
                for connection, ts, raw in reader.messages(connections=[conn]):
                    messages.append((ts, connection, raw))
            messages.sort(key=lambda x: x[0])

            times = []
            frame_idx = 0
            for ts, conn, raw in messages:
                # Deserialize (works for ROS1 and ROS2)
                msg = reader.deserialize(raw, conn.msgtype)

                # Validate message type name contains PointCloud2
                if 'PointCloud2' not in conn.msgtype:
                    # Skip any non-PointCloud2 on the same topic (rare)
                    continue

                arr = pc2_to_xyzr(msg)
                out_path = os.path.join(velodyne_dir, f"{frame_idx:06d}.bin")
                arr.tofile(out_path)

                # Timestamps: rosbags represents ts as int nanoseconds or has .nanoseconds
                if hasattr(ts, 'nanoseconds'):
                    timesec = ts.nanoseconds / 1e9
                else:
                    timesec = int(ts) / 1e9
                times.append(timesec)
                frame_idx += 1

        if times:
            with open(times_path, 'w') as f:
                for t in times:
                    f.write(f"{t:.9f}\n")
        print(f"Wrote {frame_idx} frames to {seq_dir}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bag_dir', required=True, help='Folder with .bag files (e.g., measurement_long)')
    ap.add_argument('--topic', default='/ouster/points', help='PointCloud2 topic name')
    ap.add_argument('--out_root', required=True, help='Output dataset root, will create sequences/.. here')
    args = ap.parse_args()

    convert_bags(args.bag_dir, args.topic, args.out_root)

if __name__ == '__main__':
    main()
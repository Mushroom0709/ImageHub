"""生成 200MB 伪 ARW 文件（dcraw 不可解析也无所谓——测试目标是不依赖 PIL）"""
import os
import sys
import random
import io

# PIL import
sys.path = [p for p in sys.path if 'hermes' not in p]
from PIL import Image


def make_jpeg_preview(width=800, height=600):
    random.seed(2026)
    img = Image.new('RGB', (width, height))
    px = img.load()
    for y in range(0, height, 16):
        for x in range(0, width, 16):
            c = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            for dy in range(min(16, height - y)):
                for dx in range(min(16, width - x)):
                    px[x + dx, y + dy] = c
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=70)
    return buf.getvalue()


def make_arw(path, total_size=200 * 1024 * 1024):
    """ARW = TIFF header + IFD + raw sensor data + JPEG preview
    构造简化版：让 dcraw 能抽 preview 即可
    """
    import struct
    jpeg = make_jpeg_preview()

    # TIFF header: byte order 'II' (little endian) + magic 42 + IFD0 offset
    ifd_offset = 8
    num_entries = 9
    ifd_size = 2 + num_entries * 12 + 4  # count + entries + next_ifd
    data_offset = ifd_offset + ifd_size
    raw_data_size = total_size - data_offset - len(jpeg)

    if raw_data_size < 1024 * 1024:
        raise ValueError(f"target {total_size} too small")

    jpeg_offset = data_offset + raw_data_size

    with open(path, 'wb') as f:
        # TIFF header
        f.write(b'II' + struct.pack('<HI', 0x002A, ifd_offset))
        # IFD0
        f.write(struct.pack('<H', num_entries))
        # Tag 0x0100 ImageWidth
        f.write(struct.pack('<HHII', 0x0100, 3, 1, 4000))
        # Tag 0x0101 ImageLength
        f.write(struct.pack('<HHII', 0x0101, 3, 1, 3000))
        # Tag 0x0102 BitsPerSample
        f.write(struct.pack('<HHII', 0x0102, 3, 1, 14))
        # Tag 0x0103 Compression
        f.write(struct.pack('<HHII', 0x0103, 3, 1, 1))
        # Tag 0x0106 PhotometricInterpretation (CFA)
        f.write(struct.pack('<HHII', 0x0106, 3, 1, 32803))
        # Tag 0x0111 StripOffsets
        f.write(struct.pack('<HHII', 0x0111, 4, 1, data_offset))
        # Tag 0x0116 RowsPerStrip
        f.write(struct.pack('<HHII', 0x0116, 3, 1, 3000))
        # Tag 0x0117 StripByteCounts
        f.write(struct.pack('<HHII', 0x0117, 4, 1, raw_data_size))
        # Tag 0x7200 (Sony private) - JPEG preview offset/length
        f.write(struct.pack('<HHII', 0x7200, 7, len(jpeg), jpeg_offset))
        # next IFD = 0
        f.write(struct.pack('<I', 0))
        # Raw data (随机填充)
        chunk = 4 * 1024 * 1024
        remaining = raw_data_size
        while remaining > 0:
            w = min(chunk, remaining)
            f.write(os.urandom(w))
            remaining -= w
        # JPEG preview
        f.write(jpeg)

    return os.path.getsize(path)


if __name__ == "__main__":
    out = "/tmp/test-200mb.arw"
    size = make_arw(out)
    print(f"size: {size / 1024 / 1024:.1f} MB")

    import subprocess
    r = subprocess.run(['dcraw', '-i', out], capture_output=True, text=True)
    print(f"dcraw -i: rc={r.returncode} out={r.stdout.strip()!r} err={r.stderr.strip()!r}")

    # dcraw -e 抽 preview
    tmpdir = "/tmp/arw-preview-test"
    os.makedirs(tmpdir, exist_ok=True)
    subprocess.run(['rm', '-f', f'{tmpdir}/*'])
    r = subprocess.run(['dcraw', '-e', out], cwd=tmpdir, capture_output=True, text=True)
    files = os.listdir(tmpdir)
    print(f"dcraw -e: rc={r.returncode}, generated: {files}")
    for f in files:
        print(f"  {f}: {os.path.getsize(f'{tmpdir}/{f}')} bytes")
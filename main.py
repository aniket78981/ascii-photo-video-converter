"""
Photo/video -> ASCII art converter (video audio ke saath)

Install:
    pip install opencv-python numpy pillow
    FFmpeg system me installed hona chahiye (audio + final encode ke liye)

Use:
    python main.py photo.jpg ascii_final.png
    python main.py input.mp4 ascii_final.mp4
    python ascii_video.py input.mp4 out.mp4 --cols 160 --color
    python ascii_video.py input.mp4 out.mp4 --font "C:/Windows/Fonts/consola.ttf"
"""
import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

try:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing required packages. Run: python -m pip install opencv-python numpy pillow"
    ) from exc

# Dark -> bright (bright pixel = zyada dense character)
DEFAULT_CHARS = " .:-=+*#%@"

FONT_CANDIDATES = [
    "C:/Windows/Fonts/consola.ttf",
    "C:/Windows/Fonts/cour.ttf",
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Monaco.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "DejaVuSansMono.ttf",
]


def load_font(size, custom=None):
    for path in ([custom] if custom else []) + FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    print("No monospace font found; using Pillow default. Use --font to set one.")
    return ImageFont.load_default()


def render_glyphs(chars, cw, ch, font):
    """Har character ko ek baar (ch x cw) brightness tile me render karo."""
    tiles = []
    for c in chars:
        img = Image.new("L", (cw, ch), 0)
        draw = ImageDraw.Draw(img)
        w = font.getlength(c) if hasattr(font, "getlength") else cw
        draw.text(((cw - w) / 2, 0), c, font=font, fill=255)
        tiles.append(np.array(img, dtype=np.uint8))
    return np.stack(tiles)  # (n, ch, cw)


def sort_by_density(chars, tiles):
    order = np.argsort(tiles.reshape(len(chars), -1).mean(axis=1))
    return "".join(chars[i] for i in order), tiles[order]


CLAHE = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))


def frame_to_ascii(frame, tiles, cols, rows, color, gamma=0.6):
    n, ch, cw = tiles.shape
    small = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    # Contrast boost: dark videos me bhi characters dikhen
    gray = CLAHE.apply(gray)
    gray = (255.0 * (gray / 255.0) ** gamma).astype(np.uint8)
    idx = (gray.astype(np.uint16) * (n - 1) // 255).astype(np.int32)

    block = tiles[idx]  # (rows, cols, ch, cw)
    if color:
        out = (block[..., None].astype(np.uint16) * small[:, :, None, None, :]) // 255
        out = out.astype(np.uint8).transpose(0, 2, 1, 3, 4).reshape(rows * ch, cols * cw, 3)
    else:
        out = block.transpose(0, 2, 1, 3).reshape(rows * ch, cols * cw)
        out = cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?", help="Input photo or video (if omitted, choose from a file dialog)")
    ap.add_argument("output", nargs="?", help="Output image/video path (default depends on input type)")
    ap.add_argument("--cols", type=int, default=120, help="ASCII columns (zyada = detail)")
    ap.add_argument("--font-size", type=int, default=10)
    ap.add_argument("--font", default=None, help="TTF font path")
    ap.add_argument("--chars", default=DEFAULT_CHARS)
    ap.add_argument("--color", action="store_true", help="Colored ASCII")
    ap.add_argument("--gamma", type=float, default=0.6,
                    help="<1 brighter, >1 darker (default 0.6)")
    ap.add_argument("--ratio", type=float, default=None,
                    help="Center-crop width/height, e.g. 0.5625 for 9:16 reel")
    args = ap.parse_args()

    input_path = args.input
    selected_from_dialog = input_path is None
    if input_path is None:
        try:
            import tkinter as tk
            from tkinter import filedialog
        except ModuleNotFoundError as exc:
            raise SystemExit(
                "No input file was provided and the file picker is unavailable. "
                "Run: python main.py path\\to\\photo.jpg or path\\to\\video.mp4"
            ) from exc

        root = tk.Tk()
        root.withdraw()
        input_path = filedialog.askopenfilename(
            title="Select a photo or video to convert",
            filetypes=[
                ("Photos and videos", "*.jpg *.jpeg *.png *.bmp *.webp *.tif *.tiff *.mp4 *.mov *.avi *.mkv *.wmv *.m4v"),
                ("Photo files", "*.jpg *.jpeg *.png *.bmp *.webp *.tif *.tiff"),
                ("Video files", "*.mp4 *.mov *.avi *.mkv *.wmv *.m4v"),
                ("All files", "*.*"),
            ],
        )
        root.destroy()
        if not input_path:
            raise SystemExit("No file selected. Run the script again and choose a photo or video.")

    if not os.path.isfile(input_path):
        raise SystemExit(f"Input file not found: {input_path}")

    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
    video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".m4v"}
    input_extension = Path(input_path).suffix.lower()
    is_image = input_extension in image_extensions
    if not is_image and input_extension not in video_extensions:
        raise SystemExit(
            f"Unsupported input type: {input_extension or '(no extension)'}. "
            "Choose a photo (JPG/PNG/BMP/WEBP/TIFF) or video (MP4/MOV/AVI/MKV/WMV)."
        )

    if args.output is None:
        output_extension = ".png" if is_image else ".mp4"
        if selected_from_dialog:
            project_dir = os.path.dirname(os.path.abspath(__file__))
            args.output = os.path.join(
                project_dir, "output", f"{Path(input_path).stem}_ascii{output_extension}"
            )
        else:
            args.output = f"ascii_final{output_extension}"

    output_dir = os.path.dirname(os.path.abspath(args.output))
    if output_dir and not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    if is_image and Path(args.output).suffix.lower() not in image_extensions:
        raise SystemExit(
            "Photo output must use an image extension such as .png, .jpg, or .webp."
        )

    font = load_font(args.font_size, args.font)
    cw = max(1, int(round(font.getlength("M")))) if hasattr(font, "getlength") else args.font_size // 2
    ch = args.font_size
    chars = list(dict.fromkeys(args.chars))
    tiles = render_glyphs(chars, cw, ch, font)
    chars, tiles = sort_by_density(chars, tiles)

    if is_image:
        try:
            with Image.open(input_path) as source:
                image = source.convert("RGB")
        except OSError as exc:
            raise SystemExit(f"Cannot open photo {input_path}: {exc}") from exc

        width, height = image.size
        if args.ratio:
            if width / height > args.ratio:
                crop_width = max(1, int(height * args.ratio))
                left = (width - crop_width) // 2
                image = image.crop((left, 0, left + crop_width, height))
            else:
                crop_height = max(1, int(width / args.ratio))
                top = (height - crop_height) // 2
                image = image.crop((0, top, width, top + crop_height))
            width, height = image.size

        rows = max(1, int(args.cols * (height / width) * (cw / ch)))
        frame = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
        art = frame_to_ascii(frame, tiles, args.cols, rows, args.color, args.gamma)
        art = cv2.cvtColor(art, cv2.COLOR_BGR2RGB)
        try:
            Image.fromarray(art).save(args.output)
        except OSError as exc:
            raise SystemExit(f"Could not save photo output {args.output}: {exc}") from exc
        print(f"Done -> {args.output}")
        return

    if shutil.which("ffmpeg") is None:
        raise SystemExit("FFmpeg not found in PATH. Install FFmpeg and ensure 'ffmpeg' is available.")

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise SystemExit(f"Cannot open {input_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if args.ratio:
        if W / H > args.ratio:
            W2, H2 = int(H * args.ratio), H
        else:
            W2, H2 = W, int(W / args.ratio)
    else:
        W2, H2 = W, H
    x0, y0 = (W - W2) // 2, (H - H2) // 2

    cols = args.cols
    rows = max(1, int(cols * (H2 / W2) * (cw / ch)))
    out_w, out_h = cols * cw, rows * ch
    out_w -= out_w % 2
    out_h -= out_h % 2

    tmpdir = tempfile.mkdtemp()
    silent = os.path.join(tmpdir, "silent.mp4")
    writer = cv2.VideoWriter(silent, cv2.VideoWriter_fourcc(*"mp4v"), fps, (out_w, out_h))

    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame = frame[y0:y0 + H2, x0:x0 + W2]
        art = frame_to_ascii(frame, tiles, cols, rows, args.color, args.gamma)
        writer.write(art[:out_h, :out_w])
        i += 1
        if i % 30 == 0:
            print(f"\r{i}/{total} frames", end="", flush=True)
    cap.release()
    writer.release()
    print("\nEncoding final video with audio...")

    cmd = ["ffmpeg", "-y", "-i", silent, "-i", input_path,
           "-map", "0:v:0", "-map", "1:a:0?",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
           "-c:a", "aac", "-shortest", args.output]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmpdir, ignore_errors=True)
    print(f"Done -> {args.output}")


if __name__ == "__main__":
    main()

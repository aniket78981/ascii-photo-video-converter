# ASCII Photo/Video Converter

Photo -> ASCII image, ya video -> ASCII video (audio ke saath), Python + OpenCV + Pillow + FFmpeg.

## Setup
1. Python 3.8+ aur FFmpeg install karo (Windows: `winget install ffmpeg`)
2. `python -m venv venv` then `venv\Scripts\activate`
3. `pip install -r requirements.txt`

## Run
1. Photo ya video `input/` folder me rakho.
2. Photo convert karne ke liye: `python main.py input/photo.jpg output/photo_ascii.png --cols 110`
3. Video convert karne ke liye: `python main.py input/video.mp4 output/video_ascii.mp4 --cols 110 --ratio 0.5625`
4. `python main.py` run karke file picker se photo/video select karo; output `output/` folder me save hoga.

## Options
- `--cols 160`   zyada detail
- `--color`      colored ASCII
- `--gamma 0.4`  dark video ko bright karo
- `--font "C:/Windows/Fonts/consola.ttf"`  apna font

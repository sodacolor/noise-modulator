import cv2 as cv
import numpy as np
import sys
import argparse
import time
import os

class Modulator:
    def __init__(self, resolution: tuple[int, int]):
        # initialize buffer with random values between 0 and 1
        rng = np.random.default_rng()
        self._buffer = rng.random(resolution)

    def modulate(self, source: np.ndarray, amount: float = 1):
        # resize modulation source to match internal buffer
        source_resized = cv.resize(source, dsize = self._buffer.shape[:2], interpolation = cv.INTER_NEAREST)
        if source_resized.shape != self._buffer.shape: # this checks for different numbers of color channels
            raise ValueError("source shape doesn't match buffer")

        source_normalized = source_resized / 255
        delta = source_normalized * amount
        self._buffer = (self._buffer + delta) % 1

    def render_loop(self) -> np.ndarray:
        rendered = self._buffer * 256

        return rendered.astype(np.uint8)

    def render_ping_pong(self) -> np.ndarray:
        rendered = np.abs(self._buffer * 2 - 1) * 256

        return rendered.astype(np.uint8)

def render_image(args):
    # load image from disk
    source_raw = cv.imread(args.source)
    if source_raw is None:
        sys.exit("failed to load source image")

    # process source image
    source = cv.cvtColor(source_raw, cv.COLOR_RGB2GRAY)
    source_resolution = (source.shape[0], source.shape[1])

    if args.resolution is None:
        resolution = source_resolution
    else:
        resolution = tuple(args.resolution)

    if args.fps is None:
        fps = 60
    else:
        fps = args.fps

    if args.duration is None:
        duration = 5
    else:
        duration = args.duration

    modulator = Modulator(resolution)

    frame_interval_ms = 1000 / fps
    modulation_amount = args.rate / fps

    while True:
        frame_start_time = time.perf_counter()

        modulator.modulate(source, modulation_amount)

        match args.type:
            case "loop":
                buffer = modulator.render_loop()
            case "ping_pong":
                buffer = modulator.render_ping_pong()
            case _:
                raise ValueError("invalid 'type' argument supplied")

        # unless unnecessary or told otherwise, resize modulator output to match source resolution
        if not ((buffer.shape[0], buffer.shape[1]) == source_resolution or args.output_unscaled):
            buffer = cv.resize(buffer, dsize = source_resolution, interpolation = cv.INTER_NEAREST)

        cv.imshow("preview", buffer)

        frame_time_ms = (time.perf_counter() - frame_start_time) * 1000
        wait_time = max(round(frame_interval_ms - frame_time_ms), 1)
        cv.waitKey(wait_time)

def render_video(args):
    pass

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("source", help = "path to source image or video")
    arg_parser.add_argument("-t", "--type", choices = ["loop", "ping_pong"], default = "loop", help = "modulation type")
    arg_parser.add_argument("-r", "--rate", type = float, default = 10, help = "modulation rate (default is 10)")
    arg_parser.add_argument("--resolution", nargs = 2, metavar = ("WIDTH", "HEIGHT"), type = int, help = "resolution of the internal video buffer (defaults to source resolution)")
    arg_parser.add_argument("--output-unscaled", action = "store_true", help = "outputs video at internal buffer resolution instead of source resolution")
    arg_parser.add_argument("-f", "--fps", type = int, help = "framerate of output video (defaults to 60 for image sources and source framerate for video sources)")
    arg_parser.add_argument("-d", "--duration", type = float, help = "duration of output video (defaults to 5 for image sources and source duration for video sources)")
    args = arg_parser.parse_args()

    if args.rate is not None and args.rate <= 0:
        raise ValueError("'rate' argument must be positive")
    if args.fps is not None and args.fps < 1:
        raise ValueError("'fps' argument must be positive")
    if args.duration is not None and args.duration <= 0:
        raise ValueError("'duration' argument must be positive")

    # determine source type
    source_extension = os.path.splitext(args.source)
    match source_extension:
        case "jpg" | "jpeg" | "png" | "bmp" | "gif":
            source_type = "image"
        case "mp4" | "mov" | "avi" | "flv" | "webm":
            source_type = "video"
        case _:
            raise ValueError("unsupported source file type")

    if source_type == "image":
        render_image(args)
    elif source_type == "video":
        render_video(args)

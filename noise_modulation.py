import cv2 as cv
import numpy as np
import sys
import argparse

class Modulator:
    def __init__(self, width: int, height: int):
        rng = np.random.default_rng()
        self._buffer = rng.random((width, height))

    def modulate(self, source: np.ndarray, amount: float = 1):
        source_resized = cv.resize(source, dsize = self._buffer.shape[:2], interpolation = cv.INTER_NEAREST)
        if source_resized.shape != self._buffer.shape: # this checks for different numbers of color channels
            raise ValueError("source shape doesn't match buffer")

        source_normalized = source_resized / 255
        delta = source_normalized * amount
        self._buffer = (self._buffer + delta) % 1

    def render_buffer(self) -> np.ndarray:
        rendered = np.abs(self._buffer * 2 - 1) * 256

        return rendered.astype(np.uint8)

if __name__ == "__main__":
    def parse_args():
        arg_parser = argparse.ArgumentParser()
        arg_parser.add_argument("source", help="path to source video")
        arg_parser.add_argument("-r", "--rate", type=float, default=10, help="modulation rate")
        arg_parser.add_argument("--width", type=int, help="unscaled width of output video (defaults to source width)")
        arg_parser.add_argument("--height", type=int, help="unscaled height of output video (defaults to source height)")
        arg_parser.add_argument("--scale", type=float, default=1, help="scale factor to apply to output video")
        arg_parser.add_argument("--fps", type=int, help="framerate of output video (defaults to source framerate)")
        args = arg_parser.parse_args()

        if args.rate is not None and args.rate <= 0:
            raise ValueError("'rate' argument must be positive")
        if args.width is not None and args.width < 1:
            raise ValueError("'width' argument must be positive")
        if args.height is not None and args.height < 1:
            raise ValueError("'height' argument must be positive")
        if args.scale is not None and args.scale < 1:
            raise ValueError("'scale' argument must be positive")
        if args.fps is not None and args.fps < 1:
            raise ValueError("'fps' argument must be positive")

        return args
    args = parse_args()

    source_raw = cv.imread(cv.samples.findFile(args.source))
    if source_raw is None:
        sys.exit("failed to read source video")
    cv.imshow("source", source_raw)

    source = cv.cvtColor(source_raw, cv.COLOR_RGB2GRAY)

    if args.width is None:
        args.width = source.shape[0]
    if args.height is None:
        args.height = source.shape[1]
    if args.fps is None:
        args.fps = 60 # TODO: replace with source framerate

    modulator = Modulator(args.width, args.height)

    frame_interval_ms = int(1000 / args.fps)
    modulation_amount = args.rate / args.fps

    while True:
        cv.imshow("processed source", source)

        modulator.modulate(source, modulation_amount)
        buffer = modulator.render_buffer()
        cv.imshow("buffer", cv.resize(buffer, dsize = None, fx = args.scale, fy = args.scale, interpolation = cv.INTER_NEAREST))

        cv.waitKey(frame_interval_ms)

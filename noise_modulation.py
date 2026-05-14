import cv2 as cv
import numpy as np
import sys
import argparse
import os
import datetime
import alive_progress

class Modulator:
    def __init__(self, resolution: tuple[int, int]):
        self._resolution = resolution

        # initialize buffer with random values between 0 and 1
        rng = np.random.default_rng()
        self._buffer = rng.random(resolution)

    def modulate(self, source: np.ndarray, amount: float = 1):
        # process modulation source
        source_resized = cv.resize(source, dsize = self._resolution, interpolation = cv.INTER_NEAREST) # resize modulation source to match internal buffer
        source_grayscale = cv.cvtColor(source_resized, cv.COLOR_RGB2GRAY)
        source_normalized = source_grayscale / 255

        delta = source_normalized * amount
        self._buffer = (self._buffer + delta) % 1

    def render_loop(self) -> np.ndarray:
        values = self._buffer * 256
        rendered_grayscale = values.astype(np.uint8)
        rendered = cv.cvtColor(rendered_grayscale, cv.COLOR_GRAY2RGB)

        return rendered

    def render_ping_pong(self) -> np.ndarray:
        values = np.abs(self._buffer * 2 - 1) * 256
        rendered_grayscale = values.astype(np.uint8)
        rendered = cv.cvtColor(rendered_grayscale, cv.COLOR_GRAY2RGB)

        return rendered

def render_image(args):
    # load image from disk
    source = cv.imread(args.source)
    if source is None:
        raise RuntimeError("failed to load source image")
    source_resolution = (source.shape[0], source.shape[1])

    source_file_name = os.path.basename(args.source)
    if __name__ == "__main__":
        print(f"loaded source image ({source_file_name})")

    # set unspecified arguments to default values
    resolution = source_resolution if args.resolution is None else tuple(args.resolution)
    fps = 60 if args.fps is None else args.fps
    duration = 5 if args.duration is None else args.duration
    output_file_path = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S.mp4") if args.out is None else args.out

    # initialize video writer
    output_resolution = resolution if args.output_unscaled else source_resolution
    output = cv.VideoWriter(output_file_path, cv.VideoWriter.fourcc(*"mp4v"), fps, output_resolution)

    modulator = Modulator(resolution)
    modulation_amount = args.rate / fps

    preview_window_title = f"render preview ({source_file_name})"

    frame_count = int(duration * fps)
    with alive_progress.alive_bar(frame_count, title = "rendering...") as progress_bar:
        for i in range(frame_count):
            modulator.modulate(source, modulation_amount)

            match args.type:
                case "loop":
                    frame = modulator.render_loop()
                case "ping_pong":
                    frame = modulator.render_ping_pong()
                case _:
                    raise ValueError(f"invalid 'type' argument supplied ('{args.type}')")

            # if necessary, resize frame to match output resolution
            if not (frame.shape[0], frame.shape[1]) == output_resolution:
                frame = cv.resize(frame, dsize = output_resolution, interpolation = cv.INTER_NEAREST)

            # if enabled, update render preview
            if args.preview:
                cv.imshow(preview_window_title, frame)
                cv.waitKey(1)

            output.write(frame)

            progress_bar()

        progress_bar.text("...done!")

    # clean up preview window
    if args.preview:
        cv.destroyWindow(preview_window_title)

def render_video(args):
    # load video from disk
    source = cv.VideoCapture(args.source)
    if not source.isOpened():
        raise RuntimeError("failed to load source video")
    source_resolution = (int(source.get(cv.CAP_PROP_FRAME_WIDTH)), int(source.get(cv.CAP_PROP_FRAME_HEIGHT)))
    fps = int(source.get(cv.CAP_PROP_FPS))
    source_duration = int(source.get(cv.CAP_PROP_FRAME_COUNT)) / fps

    source_file_name = os.path.basename(args.source)
    if __name__ == "__main__":
        print(f"loaded source video ({source_file_name})")

    # set unspecified arguments to default values
    resolution = source_resolution if args.resolution is None else tuple(args.resolution)
    duration = source_duration if args.duration is None else args.duration
    output_file_path = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S.mp4") if args.out is None else args.out

    # initialize video writer
    output_resolution = resolution if args.output_unscaled else source_resolution
    output = cv.VideoWriter(output_file_path, cv.VideoWriter.fourcc(*"mp4v"), fps, output_resolution)

    modulator = Modulator(resolution)
    modulation_amount = args.rate / fps

    preview_window_title = f"render preview ({source_file_name})"

    frame_count = int(duration * fps)
    with alive_progress.alive_bar(frame_count, title = "rendering...") as progress_bar:
        for i in range(frame_count):
            ret, frame = source.read()
            if not ret: # if the source has closed unexpectedly...
                raise RuntimeError("source video closed unexpectedly")

            modulator.modulate(frame, modulation_amount)

            match args.type:
                case "loop":
                    frame = modulator.render_loop()
                case "ping_pong":
                    frame = modulator.render_ping_pong()
                case _:
                    raise ValueError(f"invalid 'type' argument supplied ('{args.type}')")

            # if necessary, resize frame to match output resolution
            if not (frame.shape[0], frame.shape[1]) == output_resolution:
                frame = cv.resize(frame, dsize = output_resolution, interpolation = cv.INTER_NEAREST)

            # if enabled, update render preview
            if args.preview:
                cv.imshow(preview_window_title, frame)
                cv.waitKey(1)

            output.write(frame)

            progress_bar()
        else: # doesn't run if the loop is broken out of
            progress_bar.text("...done!")

    # clean up preview window
    if args.preview:
        cv.destroyWindow(preview_window_title)

    source.release()

if __name__ == "__main__":
    alive_progress.config_handler.set_global(spinner = False, receipt_text = True)

    # parse command line arguments
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("source", help = "path to source image or video")
    arg_parser.add_argument("-t", "--type", choices = ["loop", "ping_pong"], default = "loop", help = "modulation type")
    arg_parser.add_argument("-r", "--rate", type = float, default = 10, help = "modulation rate (default is 10)")
    arg_parser.add_argument("--resolution", nargs = 2, metavar = ("WIDTH", "HEIGHT"), type = int, help = "resolution of the internal video buffer (defaults to source resolution)")
    arg_parser.add_argument("-o", "--out", help = "output file name (defaults to 'YYYY-MM-DD_HH-MM-SS.mp4')")
    arg_parser.add_argument("--output-unscaled", action = "store_true", help = "output video at internal buffer resolution instead of source resolution")
    arg_parser.add_argument("-f", "--fps", type = int, help = "framerate of output video (default is 60, only applies to image sources)")
    arg_parser.add_argument("-d", "--duration", type = float, help = "duration of output video (defaults to 5 for image sources and source duration for video sources)")
    arg_parser.add_argument("-p", "--preview", action = "store_true", help = "show a real-time rendering preview (note: significant performance impact)")
    args = arg_parser.parse_args()

    # validate command line arguments
    if args.rate is not None and args.rate <= 0:
        raise ValueError("'rate' argument must be positive")
    if args.fps is not None and args.fps < 1:
        raise ValueError("'fps' argument must be positive")
    if args.duration is not None and args.duration <= 0:
        raise ValueError("'duration' argument must be positive")

    # determine source type
    _, source_extension = os.path.splitext(args.source)
    match source_extension:
        case ".jpg" | ".jpeg" | ".png" | ".bmp" | ".gif":
            source_type = "image"
        case ".mp4" | ".mov":
            source_type = "video"
        case _:
            raise ValueError(f"unsupported source file type ({source_extension})")

    if source_type == "image":
        render_image(args)
    elif source_type == "video":
        render_video(args)

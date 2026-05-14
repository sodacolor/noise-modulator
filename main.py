import alive_progress
import argparse
import cv2 as cv
import datetime
import math
import os
import pathlib

from modulator import *

def render_image(args):
    # load image from disk
    source = cv.imread(args.source)
    if source is None:
        raise RuntimeError("failed to load source image")

    # extract source metadata
    source_resolution = (source.shape[0], source.shape[1])

    if __name__ == "__main__":
        print(f"source: {os.path.basename(args.source)} | {"x".join(map(str, source_resolution))}")

    # initialize frame generator
    def generate_frames():
        while True:
            yield source
    frames = generate_frames()

    fps = 60 if args.fps is None else args.fps
    duration = 5.0 if args.duration is None else args.duration

    render(frames, fps, duration, args)

def render_video(args):
    # load video from disk
    source = cv.VideoCapture(args.source)
    if not source.isOpened():
        raise RuntimeError("failed to load source video")

    # extract source metadata
    source_resolution = (int(source.get(cv.CAP_PROP_FRAME_WIDTH)), int(source.get(cv.CAP_PROP_FRAME_HEIGHT)))
    fps = source.get(cv.CAP_PROP_FPS)
    source_duration = source.get(cv.CAP_PROP_FRAME_COUNT) / fps

    if __name__ == "__main__":
        print(f"source: {os.path.basename(args.source)} | {"x".join(map(str, source_resolution))} | {fps:.0f} fps | {source_duration:.1f}s")

    # initialize frame generator
    def generate_frames():
        try:
            while source.isOpened():
                ret, frame = source.read()
                if not ret: # if the source has stopped supplying frames...
                    break

                yield frame
        finally:
            source.release()
    frames = generate_frames()

    if args.duration is None:
        duration = source_duration
    else:
        if args.duration <= source_duration:
            duration = args.duration
        else:
            raise ValueError("'duration' argument must not exceed the source duration")

    render(frames, fps, duration, args)

def render(frames, fps: float, duration: float, args):
    # extract source resolution from first frame
    initial_frame = next(frames)
    source_resolution = tuple(initial_frame.shape[1::-1])

    # initialize modulator
    buffer_resolution = tuple([math.ceil(x * (args.resolution_scale / 100)) for x in source_resolution]) # apply resolution scaling
    modulator = Modulator(buffer_resolution)
    modulation_amount = args.rate / fps

    if __name__ == "__main__":
        print(f"modulator: {args.type} @ {args.rate} Hz | {"x".join(map(str, buffer_resolution))}")

    # generate default output path if necessary
    if args.out is None:
        # create renders folder at script location if necessary
        script_path = pathlib.Path(__file__).resolve()
        renders_dir_path = script_path.parent / "renders"
        renders_dir_path.mkdir(exist_ok = True)

        now = datetime.datetime.now()
        output_file_name = now.strftime("%Y-%m-%d_%H-%M-%S.mp4")

        output_file_path = renders_dir_path / output_file_name
    else:
        output_file_path = args.out
        output_file_name = os.path.basename(output_file_path)

    # initialize video writer
    output_resolution = buffer_resolution if args.output_unscaled else source_resolution
    output = cv.VideoWriter(output_file_path, cv.VideoWriter.fourcc(*"mp4v"), fps, output_resolution)

    if __name__ == "__main__":
        print(f"render: {output_file_name} | {"x".join(map(str, output_resolution))} | {fps:.0f} fps | {duration:.1f}s")

    preview_window_title = f"render preview ({os.path.basename(args.source)})"

    try:
        frame_count = int(duration * fps)
        with alive_progress.alive_bar(frame_count, title = "rendering...") as progress_bar:
            for i in range(frame_count):
                if i == 0:
                    frame = initial_frame
                else:
                    try:
                        frame = next(frames)
                    except:
                        raise RuntimeError("frame generator closed unexpectedly")

                modulator.modulate(frame, modulation_amount)

                # render the frame using a different method according to the type argument
                match args.type:
                    case "loop":
                        frame = modulator.render_loop()
                    case "ping_pong":
                        frame = modulator.render_ping_pong()
                    case _:
                        raise ValueError(f"invalid 'type' argument supplied ('{args.type}')")

                # if necessary, resize frame to match output resolution
                if frame.shape[:2] != output_resolution:
                    frame = cv.resize(frame, dsize = output_resolution, interpolation = cv.INTER_NEAREST)

                # if enabled, update render preview
                if args.preview:
                    cv.imshow(preview_window_title, frame)
                    cv.waitKey(1)

                output.write(frame)

                progress_bar()
            else: # doesn't run if the loop is broken out of
                progress_bar.text("...done!")
    # if an error occurs or the user interrupts the render, clean up incomplete output file
    except (Exception, KeyboardInterrupt) as e:
        output.release()
        output_file_path.unlink(missing_ok=True)

        raise e

    # clean up preview window
    if args.preview:
        cv.destroyWindow(preview_window_title)

    frames.close()
    output.release()

if __name__ == "__main__":
    # parse command line arguments
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("source", help = "path to source image or video")
    arg_parser.add_argument("-t", "--type", choices = ["loop", "ping_pong"], default = "loop", help = "modulation type")
    arg_parser.add_argument("-r", "--rate", type = float, default = 10, help = "modulation rate (default is 10)")
    arg_parser.add_argument("-R", "--resolution-scale", type = float, default = 50, \
                            help = "resolution of the internal video buffer compared to source resolution in percent (default is 50%%)")
    arg_parser.add_argument("-o", "--out", help = "output file path (defaults to 'renders/YYYY-MM-DD_HH-MM-SS.mp4')")
    arg_parser.add_argument("--output-unscaled", action = "store_true", \
                            help = "output video at internal buffer resolution instead of source resolution")
    arg_parser.add_argument("-f", "--fps", type = float, \
                            help = "framerate of output video (default is 60, only applies to image sources)")
    arg_parser.add_argument("-d", "--duration", type = float, \
                            help = "duration of output video (defaults to 5 for image sources and source duration for video sources)")
    arg_parser.add_argument("-p", "--preview", action = "store_true", \
                            help = "show a real-time rendering preview (note: significant performance impact)")
    args = arg_parser.parse_args()

    # validate command line arguments
    if args.rate is not None and args.rate <= 0:
        raise ValueError("'rate' argument must be positive")
    if args.resolution_scale is not None and args.resolution_scale <= 0:
        raise ValueError("'resolution-scale' argument must be positive")
    if args.fps is not None and args.fps <= 0:
        raise ValueError("'fps' argument must be positive")
    if args.duration is not None and args.duration <= 0:
        raise ValueError("'duration' argument must be positive")

    # set global progress bar config
    alive_progress.config_handler.set_global(receipt_text = True)

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
        if args.fps is not None:
            raise ValueError("'fps' argument is incompatible with video sources")

        render_video(args)

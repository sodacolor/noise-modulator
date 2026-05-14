import cv2 as cv
import numpy as np

class Modulator:
    def __init__(self, resolution: tuple[int, int]):
        # initialize buffer with random values between 0 and 1
        rng = np.random.default_rng()
        self._buffer = rng.random(resolution[::-1])

    def modulate(self, source: np.ndarray, amount: float = 1):
        # process modulation source
        source_resized = cv.resize(source, dsize = self._buffer.shape[2::-1], interpolation = cv.INTER_NEAREST) # resize modulation source to match internal buffer
        source_grayscale = cv.cvtColor(source_resized, cv.COLOR_RGB2GRAY)
        source_normalized = source_grayscale / 255

        delta = source_normalized * amount
        self._buffer = (self._buffer + delta) % 1

    def render_loop(self):
        values = self._buffer * 256
        rendered_grayscale = values.astype(np.uint8)
        rendered = cv.cvtColor(rendered_grayscale, cv.COLOR_GRAY2RGB)

        return rendered

    def render_ping_pong(self):
        values = np.abs(self._buffer * 2 - 1) * 256
        rendered_grayscale = values.astype(np.uint8)
        rendered = cv.cvtColor(rendered_grayscale, cv.COLOR_GRAY2RGB)

        return rendered

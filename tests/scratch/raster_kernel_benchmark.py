from time import perf_counter

import numpy

from core_pdf.impl.engine.rendering import rasterize_unclipped_line_normal


def main():
    iterations = 80
    width = 96
    height = 96
    pixels = bytearray(width * height * 4)
    target = numpy.frombuffer(pixels, dtype=numpy.uint8).reshape(height, width, 4)
    x_coords = numpy.arange(8, 88, dtype=numpy.float64)
    y_coords = numpy.arange(8, 88, dtype=numpy.float64)

    started = perf_counter()
    for _ in range(iterations):
        target.fill(0)
        rasterize_unclipped_line_normal(
            pixels,
            width,
            0.0,
            96.0,
            1.0,
            8.0,
            12.0,
            84.0,
            76.0,
            1.5,
            (32, 96, 192, 220),
            0,
            (8, 8, 88, 88),
            target_pixels=target,
            x_coords=x_coords,
            y_coords=y_coords,
        )

    elapsed = perf_counter() - started
    print(
        "mean_ms=%.3f checksum=%d"
        % (elapsed / iterations * 1000.0, int(numpy.asarray(target).sum()))
    )


if __name__ == "__main__":
    main()

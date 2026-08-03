from pathlib import Path
import sys
from time import perf_counter

from core_pdf import PdfDocument


def main():
    path = Path(sys.argv[1])
    iterations = int(sys.argv[2])
    times = []
    output_length = 0
    for _ in range(iterations):
        started = perf_counter()
        with PdfDocument.open(path) as document:
            page = document.pages[0]
            page.extract()
            output_length = len(page.to_markdown())
        times.append(perf_counter() - started)
    warm = times[1:]
    print(
        "warm_mean_ms=%.3f warm_min_ms=%.3f output=%d"
        % (sum(warm) / len(warm) * 1000, min(warm) * 1000, output_length)
    )


if __name__ == "__main__":
    raise SystemExit(main())

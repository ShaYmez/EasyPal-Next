"""Future RX waterfall text decoder."""

from __future__ import annotations

import numpy as np


class WaterfallTextDecoder:
    def decode(self, samples: np.ndarray) -> str | None:
        raise NotImplementedError("Waterfall RX text decoding planned for v2")

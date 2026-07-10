"""Waterfall spectrum painting abstract interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np


class WaterfallPainter(ABC):
    @abstractmethod
    def text_to_audio(self, text: str, *, font: str, font_size: int) -> np.ndarray: ...

    @abstractmethod
    def image_to_audio(self, image_path: Path) -> np.ndarray: ...

    @abstractmethod
    def save_wav(self, samples: np.ndarray, path: Path, sample_rate: int) -> Path: ...

    @abstractmethod
    def load_wav(self, path: Path) -> np.ndarray: ...

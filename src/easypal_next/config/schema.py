"""Pydantic configuration models."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class CatRadioConfig(BaseModel):
    profile: Literal["cat"] = "cat"
    rig_model: int = 3073
    port: str = "COM3"
    baud: int = 115200
    ptt_method: Literal["rig", "data"] = "data"


class SerialPttConfig(BaseModel):
    profile: Literal["serial"] = "serial"
    port: str = "COM4"
    line: Literal["RTS", "DTR"] = "RTS"
    active_low: bool = False
    baud: int = 9600


class VoxManualConfig(BaseModel):
    profile: Literal["vox"] = "vox"
    pre_tx_delay_ms: int = 300
    post_tx_delay_ms: int = 200


RadioConfig = Annotated[
    Union[CatRadioConfig, SerialPttConfig, VoxManualConfig],
    Field(discriminator="profile"),
]


class AudioConfig(BaseModel):
    input_device: int | None = None
    output_device: int | None = None
    sample_rate: int = 48000
    block_size: int = 1024


class ModemConfig(BaseModel):
    mode: str = "DATAC3"
    sample_rate: int = 8000
    libcodec2_path: str | None = None
    fsk_M: int = 2
    fsk_Rs: int = 100
    fsk_Fs: int = 8000
    ldpc_codename: str = "H_256_512_4"
    """Transfer modem stack: HamDRM (EasyPal run.dll) or FreeDV (libcodec2)."""
    engine: Literal["hamdrm", "freedv"] = "hamdrm"
    hamdrm_dll_path: str | None = None
    hamdrm_mode: Literal["A", "B", "E"] = "B"
    hamdrm_specocc: Literal["2.3", "2.5"] = "2.3"
    hamdrm_mscprot: Literal["normal", "low"] = "normal"
    hamdrm_qam: Literal[4, 16, 64] = 16
    hamdrm_interleave: Literal["short", "long"] = "short"
    hamdrm_dc_freq: int = 350
    """Lead-in / start delay symbols (EasyPal default profile uses 24)."""
    hamdrm_start_delay: int = 12


class FecConfig(BaseModel):
    k: int = 16
    m: int = 24
    chunk_size: int = 1024


class TransferConfig(BaseModel):
    loopback_mode: bool = True
    """Milliseconds to wait after each modem burst (0 = fastest; use 5–20 on-air if needed)."""
    pace_ms: int = 0
    """Max duration for on-air Tune (three-tone 720/1466/1840 Hz)."""
    tune_max_seconds: int = 5
    """Radio emission mode — guides Tune hints (FM, AM, or SSB/USB)."""
    radio_emission: Literal["fm", "am", "ssb"] = "fm"
    """When on-air, keep listening and accept incoming transfers automatically."""
    auto_rx: bool = True
    """Transmit callsign as WFTxt on the air before Tune / file TX / WFTxt body."""
    require_callsign_wftxt_header: bool = True
    """Silence after callsign header before Tune tone / file TX / WFTxt body (seconds)."""
    callsign_header_gap_seconds: float = 1.0


class WaterfallConfig(BaseModel):
    enabled: bool = True
    """Live scrolling spectrum from audio input / TX monitor."""
    live_enabled: bool = True
    """Paint sample rate — EasyPal WFTxt WAVs use 25000 Hz."""
    sample_rate: int = 25000
    freq_min_hz: int = 100
    freq_max_hz: int = 2500
    """Milliseconds per bitmap column (~41 ms matches EasyPal fix-n / bsr-n)."""
    line_time_ms: float = 41.0
    line_repeats: int = 1
    default_font: str = "Tahoma"
    default_font_size: int = 24
    """EasyPal negative paint: fill band, cut letter holes. Off by default —
    full-canvas invert turns padding into noise clicks."""
    negative_paint: bool = False
    begin_message: str = "<< EASYPAL >>"
    end_message: str = ""
    begin_wav: str | None = None
    end_wav: str | None = None
    tx_monitor: bool = True
    colormap: Literal["green", "heat", "grayscale"] = "grayscale"
    min_db: float = -60.0
    max_db: float = 0.0
    """FFT size — larger = finer frequency detail, slower updates."""
    fft_size: int = 4096
    """GUI refresh interval for spectrum rows (ms). Lower = faster scroll."""
    fft_interval_ms: int = 50
    """FFT window function (Hann is typical for SDR / spectrograms)."""
    fft_window: Literal["none", "hann", "hamming", "blackman"] = "hann"
    """Overlap fraction between FFT frames (0–0.875). Higher = smoother waterfall."""
    fft_overlap: float = 0.8
    """History lines kept in the scrolling buffer (time axis depth)."""
    history_rows: int = 512
    """Lines to advance the waterfall per FFT row (scroll speed)."""
    scroll_pixels: int = 1


class UiConfig(BaseModel):
    theme: Literal["light", "dark"] = "light"


class NetworkConfig(BaseModel):
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8765
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    gallery_dir: str | None = None
    received_dir: str | None = None


class CommunityServerConfig(BaseModel):
    enabled: bool = False
    base_url: str | None = None
    api_key: str | None = None
    hybrid_enabled: bool = False
    auto_upload_rx: bool = False
    upload_transport: Literal["rest", "ftp"] = "rest"
    ftp_host: str | None = None
    ftp_user: str | None = None
    ftp_password: str | None = None
    ftp_remote_dir: str = "/"


class AppConfig(BaseModel):
    callsign: str = "N0CALL"
    audio: AudioConfig = Field(default_factory=AudioConfig)
    modem: ModemConfig = Field(default_factory=ModemConfig)
    radio: RadioConfig = Field(default_factory=VoxManualConfig)
    fec: FecConfig = Field(default_factory=FecConfig)
    waterfall: WaterfallConfig = Field(default_factory=WaterfallConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    community: CommunityServerConfig = Field(default_factory=CommunityServerConfig)
    transfer: TransferConfig = Field(default_factory=TransferConfig)
    ui: UiConfig = Field(default_factory=UiConfig)

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
    libcodec2_path: str | None = None
    fsk_M: int = 2
    fsk_Rs: int = 100
    fsk_Fs: int = 8000
    ldpc_codename: str = "H_256_512_4"


class FecConfig(BaseModel):
    k: int = 16
    m: int = 24
    chunk_size: int = 1024


class WaterfallConfig(BaseModel):
    enabled: bool = True
    sample_rate: int = 48000
    freq_min_hz: int = 500
    freq_max_hz: int = 2500
    line_time_ms: float = 8.0
    line_repeats: int = 2
    default_font: str = "DejaVu Sans Mono"
    default_font_size: int = 16
    begin_message: str = "<< EASYPAL >>"
    end_message: str = ""
    begin_wav: str | None = None
    end_wav: str | None = None
    tx_monitor: bool = True


class NetworkConfig(BaseModel):
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8765
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    gallery_dir: str | None = None


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


class TransferConfig(BaseModel):
    loopback_mode: bool = True


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

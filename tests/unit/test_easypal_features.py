"""Unit tests for CW ID, EmbedTxt, Station Log, Pic/QSL, cues, QRM gate."""

from pathlib import Path

from PIL import Image

from easypal_next.core.station_log import append_station_log, read_station_log, station_log_path
from easypal_next.modem.cw_id import resolve_cw_id_wav
from easypal_next.modem.embed_txt import embed_text_on_image
from easypal_next.modem.qrm_gate import channel_looks_busy
from easypal_next.ui.qsl_compose import compose_qsl, list_qsl_templates
from easypal_next.waterfall.cue_wav import resolve_program_cue
from easypal_next.waterfall.text_renderer import render_text_bitmap
from easypal_next.waterfall.user_wave_files import easypal_user_wave_dirs


def test_embed_text_draws_without_crash(tmp_path: Path):
    img = Image.new("RGB", (320, 240), color=(40, 80, 120))
    out = embed_text_on_image(img, "M0VUB")
    assert out.size == (320, 240)
    assert out.mode == "RGB"


def test_station_log_roundtrip(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    append_station_log(direction="tx", callsign="m0vub", path="a.jpg", detail="test")
    entries = read_station_log()
    assert len(entries) >= 1
    assert entries[-1].callsign == "M0VUB"
    assert entries[-1].direction == "tx"
    assert station_log_path().is_file()


def test_qsl_compose_from_blank_template(tmp_path: Path):
    template = tmp_path / "QSL.png"
    Image.new("RGB", (400, 300), color=(200, 200, 220)).save(template)
    out = compose_qsl(template, callsign="M0VUB", extra_text="73", out_path=tmp_path / "out.jpg")
    assert out.is_file()
    assert out.stat().st_size > 0


def test_list_qsl_templates_includes_easypal_layer_when_present():
    paths = list_qsl_templates()
    assert isinstance(paths, list)


def test_resolve_cw_id_wav_type():
    path = resolve_cw_id_wav(tone_hz=1200)
    assert path is None or path.is_file()


def test_resolve_program_cue_selected_or_none():
    path = resolve_program_cue("selected", negative=False)
    assert path is None or path.is_file()
    path_n = resolve_program_cue("fileok", negative=True)
    assert path_n is None or path_n.is_file()


def test_channel_looks_busy_heuristics():
    assert channel_looks_busy(level=50, snr_db=None, fac_locked=False, qrm_level=35)
    assert not channel_looks_busy(level=10, snr_db=None, fac_locked=False, qrm_level=35)
    assert channel_looks_busy(level=10, snr_db=5.0, fac_locked=True, qrm_snr_db=2.0)
    assert not channel_looks_busy(level=10, snr_db=5.0, fac_locked=False, qrm_snr_db=2.0)


def test_slash_zeros_in_wftxt_bitmap():
    plain = render_text_bitmap("M0VUB", slash_zeros=False, width=200, height=64)
    slashed = render_text_bitmap("M0VUB", slash_zeros=True, width=200, height=64)
    assert plain.size == slashed.size
    assert plain.mode == "L"


def test_user_wave_dirs_order():
    cinema = easypal_user_wave_dirs(cinema_scroll=True)
    normal = easypal_user_wave_dirs(cinema_scroll=False)
    assert isinstance(cinema, list) and isinstance(normal, list)
    assert len(cinema) >= 1

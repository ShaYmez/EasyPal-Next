"""Main window menu bar and toolbar."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMainWindow, QToolBar


@dataclass
class MainActions:
    load_pic: QAction
    pic_qsl: QAction
    preferences: QAction
    exit_app: QAction
    transmit: QAction
    receive: QAction
    abort: QAction
    tune: QAction
    send_wftxt: QAction
    send_wfpic: QAction
    send_cw_id: QAction
    fix_bsr: QAction
    fast_bsr: QAction
    answer_bsr: QAction
    del_bsr: QAction
    open_corrupt: QAction
    station_log: QAction
    waterfall_tx_on_file: QAction
    live_waterfall: QAction
    auto_rx: QAction
    theme_light: QAction
    theme_dark: QAction
    open_gallery: QAction
    about: QAction


def build_menus(window: QMainWindow, gallery_url: str) -> MainActions:
    actions = MainActions(
        load_pic=QAction("&LoadPic", window),
        pic_qsl=QAction("Pic/&QSL…", window),
        preferences=QAction("&Preferences…", window),
        exit_app=QAction("E&xit", window),
        transmit=QAction("&Transmit", window),
        receive=QAction("&Receive", window),
        abort=QAction("&Abort", window),
        tune=QAction("&Tune", window),
        send_wftxt=QAction("Send &WFTxt", window),
        send_wfpic=QAction("Send WF&Pic…", window),
        send_cw_id=QAction("Send &CW ID", window),
        fix_bsr=QAction("&FIX / BSR", window),
        fast_bsr=QAction("Fast &BSR", window),
        answer_bsr=QAction("&Answer BSR", window),
        del_bsr=QAction("&Del BSR", window),
        open_corrupt=QAction("Open &Corrupt folder", window),
        station_log=QAction("Station &Log…", window),
        waterfall_tx_on_file=QAction("Waterfall TX on &file", window),
        live_waterfall=QAction("Live &waterfall", window),
        auto_rx=QAction("&Auto RX", window),
        theme_light=QAction("&Light theme", window),
        theme_dark=QAction("&Dark theme", window),
        open_gallery=QAction("&Open gallery in browser", window),
        about=QAction("&About EasyPal-Next", window),
    )

    actions.load_pic.setShortcut(QKeySequence("Ctrl+O"))
    actions.load_pic.setStatusTip("Select image or file to transmit")
    actions.pic_qsl.setStatusTip("Compose a QSL card from EasyPal Layer templates")
    actions.preferences.setShortcut(QKeySequence("Ctrl+,"))
    actions.transmit.setShortcut(QKeySequence("F5"))
    actions.receive.setShortcut(QKeySequence("F6"))
    actions.abort.setShortcut(QKeySequence("Esc"))
    actions.tune.setShortcut(QKeySequence("F8"))
    actions.tune.setCheckable(True)
    actions.send_wftxt.setShortcut(QKeySequence("F7"))
    actions.send_wfpic.setStatusTip("Paint an image on the waterfall (UserWaveFiles)")
    actions.send_cw_id.setStatusTip("Play EasyPal ID1200.wav CW ID via WinMM")
    actions.fix_bsr.setStatusTip("Request missing HamDRM segments (GetBSR + SendBSR)")
    actions.fast_bsr.setStatusTip("Fast BSR request (compressed; newer peers only)")
    actions.answer_bsr.setStatusTip("Resend segments for an incoming BSR request")
    actions.del_bsr.setStatusTip("Clear local BSR scratch files")
    actions.open_corrupt.setStatusTip("Open the Corrupt folder used for BSR state")
    actions.waterfall_tx_on_file.setCheckable(True)
    actions.live_waterfall.setCheckable(True)
    actions.auto_rx.setCheckable(True)
    actions.theme_light.setCheckable(True)
    actions.theme_dark.setCheckable(True)

    file_menu = window.menuBar().addMenu("&File")
    file_menu.addAction(actions.load_pic)
    file_menu.addAction(actions.pic_qsl)
    file_menu.addAction(actions.preferences)
    file_menu.addSeparator()
    file_menu.addAction(actions.exit_app)

    transfer_menu = window.menuBar().addMenu("&Transfer")
    transfer_menu.addAction(actions.transmit)
    transfer_menu.addAction(actions.receive)
    transfer_menu.addAction(actions.auto_rx)
    transfer_menu.addAction(actions.tune)
    transfer_menu.addAction(actions.send_cw_id)
    transfer_menu.addSeparator()
    transfer_menu.addAction(actions.fix_bsr)
    transfer_menu.addAction(actions.fast_bsr)
    transfer_menu.addAction(actions.answer_bsr)
    transfer_menu.addAction(actions.del_bsr)
    transfer_menu.addAction(actions.open_corrupt)
    transfer_menu.addSeparator()
    transfer_menu.addAction(actions.abort)

    waterfall_menu = window.menuBar().addMenu("&Waterfall")
    waterfall_menu.addAction(actions.send_wftxt)
    waterfall_menu.addAction(actions.send_wfpic)
    waterfall_menu.addAction(actions.live_waterfall)
    waterfall_menu.addAction(actions.waterfall_tx_on_file)

    view_menu = window.menuBar().addMenu("&View")
    view_menu.addAction(actions.theme_light)
    view_menu.addAction(actions.theme_dark)
    view_menu.addSeparator()
    view_menu.addAction(actions.station_log)
    view_menu.addAction(actions.open_gallery)

    help_menu = window.menuBar().addMenu("&Help")
    help_menu.addAction(actions.about)

    actions.open_gallery.setStatusTip(gallery_url)

    return actions


def build_toolbar(window: QMainWindow, actions: MainActions) -> QToolBar:
    toolbar = QToolBar("Main", window)
    toolbar.setMovable(False)
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
    window.addToolBar(toolbar)
    toolbar.addAction(actions.load_pic)
    toolbar.addAction(actions.transmit)
    toolbar.addAction(actions.receive)
    toolbar.addAction(actions.auto_rx)
    toolbar.addAction(actions.tune)
    toolbar.addAction(actions.fix_bsr)
    toolbar.addAction(actions.abort)
    return toolbar

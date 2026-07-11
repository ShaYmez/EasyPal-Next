# Original EasyPal Feature Matrix (Windows Install Mining)

Mined from a live Windows install for EasyPal-Next interop planning.  
Sources: `Language.english` (Ver:29B/JAN/2014), `updateinfo.text` (through **07 OCT 2014**), `C:\Program Files\EasyPal\`, `%APPDATA%\EasyPal\`, and filesystem search for `hamdrm.dll`.

---

## 1. Install paths and version

| Item | Value |
|------|--------|
| Program install | `C:\Program Files\EasyPal\` |
| Per-user data (W7+) | `C:\Users\<user>\AppData\Roaming\EasyPal\` |
| Per-user data (XP, historical) | `C:\Documents and Settings\<user>\Application Data\EasyPal` |
| Executable | `EasyPal.exe` — **PE32 GUI**, timestamp **07 Oct 2014** (`4192256` bytes) |
| Changelog tip | `misc\updateinfo.text` header **07 OCT 2014** |
| Language map | `misc\Language.english` — **Ver:29B/JAN/2014** |
| Architecture note (2011-10-01) | Install under Program Files; writable data moved to Application Data / Roaming |

### Files under `C:\Program Files\EasyPal\`

| Path | Role |
|------|------|
| `EasyPal.exe` | Main Delphi GUI (Oct 2014) |
| `EasyPal.exe.local` | Empty/local activation marker |
| `run.dll` | **DRM modem / audio / PTT / BSR core** (see §7) — *not* named `hamdrm.dll` |
| `rscoder.dll` | Reed–Solomon encode/decode (`encode_rs`, `decode_rs`, `init_rscoder`, `SetRsBSRPath`) |
| `inpout32.dll` | Parallel-port PTT (`Out32`) |
| `unins000.exe` / `unins000.dat` | Inno-style uninstaller |
| `Hybrid\` | Hybrid-mode scratch (install-tree copy; often empty) |
| `Movies\` | Movie drop / RX display folder (install-tree) |
| `RxFiles\` / `TxFiles\` | Legacy RX/TX file folders under install tree |

**Not present in Program Files:** `hamdrm.dll`, language files, program WAVs, Corrupt/Inbox (those live under Roaming after the 2011 layout change).

---

## 2. Directory map and EasyPal-Next path suggestions

### 2.1 `%APPDATA%\EasyPal\` layout

| Original path | Purpose (from menus + changelog) | Suggested EasyPal-Next mapping |
|---------------|----------------------------------|--------------------------------|
| `Inbox\` | Successfully received pictures/files | `%APPDATA%\EasyPal-Next\gallery\` (and/or `received\`) |
| `Corrupt\` | Partial RX / BSR segment state; auto-cleaned on start/shutdown; can grow huge | `%APPDATA%\EasyPal-Next\corrupt\` or `bsr\` — retain only repair metadata |
| `Sent Items\` | Outbound archive | `%APPDATA%\EasyPal-Next\sent\` |
| `Autosave\` | Autosaved RX artifacts (purge UI: AUTOSAVE) | `%APPDATA%\EasyPal-Next\autosave\` |
| `AutosaveTX\` | Autosaved TX artifacts (AUTOSAVETX) | `%APPDATA%\EasyPal-Next\autosave_tx\` |
| `Repeater\` | Repeater directory / repeated files (`Rptr` → external `\Repeater\`) | `%APPDATA%\EasyPal-Next\repeater\` (P2) |
| `BeaconFiles\` | Images for repeater beacon random TX (JPG/JP2/BMP/GIF) | `%APPDATA%\EasyPal-Next\beacon\` (P2) |
| `Movies\` | Hybrid/movie RX (`Mov` tab); also under Program Files | `%APPDATA%\EasyPal-Next\movies\` (P2) |
| `Hybrid\` | Hybrid upload/download workspace (also under Program Files) | `%APPDATA%\EasyPal-Next\hybrid\` (P1 stub exists) |
| `UserWaveFiles\` | **Reverse** waterfall WAV library (cinema bottom→top) | `%APPDATA%\EasyPal-Next\wav\user_reverse\` |
| `UserWaveFiles-N\` | **Normal** (original) waterfall WAV library | `%APPDATA%\EasyPal-Next\wav\user_normal\` |
| `programwavfiles\` | Built-in cue WAVs (`bsr`, `tune`, `beacon`, `fileok`, … + `-n` negative variants) | Bundle under `resources/wav/` + optional user override dir |
| `Transient\` | Runtime scratch (CW IDs `ID1200.wav`/`ID300.wav`, FTP helper, test images, callsign token) | `%APPDATA%\EasyPal-Next\transient\` (temp; clearable) |
| `misc\` | Languages, QSL art, `updateinfo.text`, UI images | Ship docs/i18n under repo; user overrides in AppData |
| `plugins\JPEG2000.dll` | JP2 decode support | Optional Pillow/OpenJPEG; no need for this DLL |
| `FavoriteForms\` | Saved ICS/MARS/etc. form templates | `%APPDATA%\EasyPal-Next\forms\` (P2) |
| `Layer\` | QSL/layer compose scratch | `%APPDATA%\EasyPal-Next\layers\` (P2) |
| `Spare\` | Weather bat/text helpers, zip/unzip, FTP spare | Optional / do not port wholesale |
| Root helpers | `ftps.exe`, `zip.exe`, `unzip.exe`, `iview.exe`, `booruCam.exe`, `c16.exe`/`c32.exe`, `userwx*.bat` | Prefer Python libs (httpx/aioftp, Pillow); no Win32 helpers |

### 2.2 Other historical paths

| Path | Purpose |
|------|---------|
| Drive-root `EasyPalCommonRepeaterDir` | Shared repeater directory across multiple EasyPal instances (`Rptr` → Use Common Repeater Directory) |
| `app.cfg` (referenced in exe / changelog) | Settings persistence; delete to reset — **not found** on this fresh/mined tree (generated after first run) |

### 2.3 EasyPal-Next today

| EasyPal-Next path | Role |
|-------------------|------|
| `%APPDATA%\EasyPal-Next\` | User data root (`paths.user_data_dir`) |
| `config.yaml` | Settings (replaces `app.cfg`) |
| `gallery\` | Decoded images + LAN gallery |
| `logs\` | App logs |
| Modem | **Codec2 / FreeDV DATAC3** via `libcodec2.dll` — **not** original DRM |

---

## 3. Feature matrix

**Priority key**

- **P0** — Required for **send/receive with original EasyPal** and/or **always-on RX** (Erik-era DRM workflow).
- **P1** — Strongly expected by EasyPal users; needed soon after wire interop.
- **P2** — Nice-to-have / niche (repeater ops, QSL art, multi-language polish, etc.).

**EasyPal-Next status** as of mining date (v0.2.x codebase): *Partial* / *Stub* / *Missing* / *Different design* (modern substitute, not DRM-compatible).

| Feature | Original behavior | Priority | EasyPal-Next status |
|---------|-------------------|----------|---------------------|
| Always-on RX | App initializes then continuously listens; waterfall shows live RX; TX toggles via TRANSMIT (red = TX); no separate “arm RX” for normal use | **P0** | **Partial** — `transfer.auto_rx` exists but **defaults false**; loopback default; not DRM |
| DRM OFDM TX/RX | Modes A/B/E, BW ~2.4 kHz, HI/LO, QAM 4/16/64 via `run.dll` | **P0** | **Missing / Different** — DATAC3 Codec2 only |
| Default TX profile | Menu: **B/2.4/HI/16/24** “good all round” | **P0** | **Missing** (no DRM params) |
| RS encode depth | RS1–RS4 (Very Light → Heavy); **RS2 = Light Encode** default-class | **P0** | **Different** — zfec k/m, not EasyPal RS1–4 |
| Lead-in | GUI **LeadIn**; quick profiles use **24** (or **12** for fastest/Hybrid tip) | **P0** | **Missing** as DRM lead-in; has modem preamble / Tune |
| FAC / MSC / sync / SNR | Labels FAC, MSC, Frame, Sync, SNR dB; green FAC lock | **P0** | **Missing** (no FAC/MSC) |
| Image TX (LoadPic / LoadAny) | Load image or arbitrary file; downsize options; TRANSMIT | **P0** | **Partial** — LoadPic + file transfer over DATAC3 |
| Image RX → Inbox | Decode → save under `\Inbox\`; progressive display option | **P0** | **Partial** — gallery save; not DRM Inbox semantics |
| Segment progress | Total / OK Segs / Position / remaining segments | **P0** | **Partial** — transfer progress events |
| BSR (Bad Segment Repair) | Automatic BSR (recommended) or user-select; Corrupt folder; FIX / Fast BSR / Del BSR | **P0** | **Missing** — WFTxt preset string only (`**** BSR REQUEST ****`) |
| Repeat Header | Highly recommended Always ON | **P0** | **Missing** (DRM header concept) |
| Soundcard select by name | Persists across driver changes; warning if missing | **P0** | **Partial** — PortAudio device indices |
| PTT: VOX | Default-friendly path | **P0** | **Done** — `vox` profile |
| PTT: COM RTS/DTR | CommPort PTT | **P0** | **Done** — serial PTT |
| PTT: CAT | CommPort CAT + Action → CAT Commands | **P1** | **Partial** — Hamlib CAT |
| Callsign | Setup + GUI; tag RX with callsign/time/mode | **P0** | **Partial** — `callsign` in config |
| Tune | Action → Tune; button TUNE; `tune.wav` | **P0** | **Done** — Tune session (on-air, not DRM tone set) |
| Waterfall live RX | Continuous spectrum; AGC; reverse R/N; color; seconds bar | **P0** | **Partial** — live FFT waterfall |
| WFTxt / WFPic | Waterfall text & picture TX; begin/end.wav; negative recommended | **P1** | **Partial** — WFTxt encoder; no full WFPic parity |
| Wait TX while QRM | Recommended always ON | **P0** | **Missing** |
| TX mode = RX mode | Needed with old BSR | **P0** | N/A until DRM+BSR |
| Unattended / no popups | Setup → Unattended | **P1** | **Missing** |
| Hybrid TX | Upload file; TX short retrieval code over air; RX auto-downloads | **P1** | **Stub** — `community/hybrid.py` + `HYBRID_REF` packet type |
| User-defined Hybrid server | HybridFiles / OnlineCallsigns / RxOkNotifications dirs | **P1** | **Partial** — community REST/FTP config, not full parity |
| Ignore Hybrid in normal mode | Setup/Hybrid menu | **P2** | **Missing** |
| Repeater (base / beacon / interrogate) | Large `Rptr` menu; directories; remote control | **P2** | **Missing** |
| FTP auto-upload / ONAIR / banned | FTP menu | **P2** | **Partial** — FTP client + community flags |
| CHAT mode | Yellow RX / blue TX text boxes | **P2** | **Missing** |
| Send Form (ICS213 / MARS) | Action → Send Form | **P2** | **Missing** |
| Session Log / Station Log | Action + GUI | **P2** | **Partial** — log panel |
| CW ID | 1200 Hz end-of-TX; 300 Hz ~60 s | **P2** | **Missing** (Transient has ID WAVs in original) |
| Webcam / Hamcam | Load Webcam; repeater request | **P2** | **Missing** |
| Twain acquire | Scanner | **P2** | **Missing** |
| QSL templates / Pic/QSL | Layers, shadow, custom | **P2** | **Missing** |
| GUI color / image / i18n | Many languages; F12 language export | **P2** | **Partial** — light/dark theme only |
| Movies (Mov tab) | Hybrid movie TX/RX → `\Movies\` | **P2** | **Missing** |
| Detect remote RX success (RS + internet) | Abort TX when remote decoded | **P2** | **Missing** |
| Parallel-port PTT | `inpout32.dll` | **P2** | **Missing** (obsolete) |
| Multi-instance TX / common repeater dir | Advanced ops | **P2** | **Missing** |
| LAN gallery / mobile view | — | — | **Done** (Next-only) |
| Loopback validation | — | — | **Done** (Next-only) |

---

## 4. Always-on RX behavior notes

From UI semantics and changelog (esp. TX/RX toggle, waterfall, Hybrid RX auto-sense):

1. **Default posture is receive.** After “WAIT - INITIALIZING”, the waterfall runs and the RX path is live.
2. **TRANSMIT is a toggle.** Button turns red while transmitting; click again = abort (ABORT button removed Jul 2011).
3. **Hybrid:** “For RX, there is no need to check any of the Hybrid selections… EasyPal will automatically sense any mode and decode correctly.”
4. **Normal vs Hybrid TX:** With Hybrid TX unchecked, all TX is DRM; both normal and Hybrid payloads still decode on RX unless “Ignore Hybrid Pics in normal mode” is set.
5. **Upload/download pauses RX:** During Hybrid HTTP transfer, the RX thread is disabled and the waterfall stops (Feb 2014) to avoid crashes.
6. **QRM gate:** “Wait TX while QRM (recommended always ON)” delays TX if the channel looks busy.
7. **TX waterfall caution:** Activating TX waterfall can suppress the DRM data stream / cause RX crashes for peers; boots with TX waterfall **OFF** by default; PTT disabled when TX waterfall is on (May 2012).

**EasyPal-Next gap:** Auto RX is opt-in and DATAC3-triggered; loopback defaults on. For original-user feel + interop, always-on DRM listen must become the default on-air posture.

---

## 5. Tune / waterfall / BSR / Hybrid / Repeater notes

### 5.1 Tune

- Menu: **Action → Tune**; toolbar **TUNE**.
- Program WAV: `programwavfiles\tune.wav`.
- Purpose: audio/drive calibration into the waterfall (not a file transfer).
- Related: Waterfall Options → WWV Calibration / audio calibration (±~12 Hz per pixel historically).

### 5.2 Waterfall

- **Options:** Full-screen behavior, AGC, reverse **R/N**, color, “Show Pic in Waterfall”, Activate TX Waterfall.
- **Direction (Jun 2011):** Bottom→top (“cinema”) preferred for text/pics; WAVs split across `UserWaveFiles` (reverse) vs `UserWaveFiles-N` (normal).
- **Cues:** User `begin.wav` / `end.wav`; program cues use **negative** (white-on-black inverted) for faster RX sync.
- **Save W/F:** Stop waterfall → Save W/F → Last RX Pictures.
- **WFTxt / WFPic** buttons on main UI; slash-zeros in typed waterfall text.

### 5.3 BSR

- Setup: **BSR Mode Automatic (recommended)** vs **BSR Mode User Select (advanced)**.
- Corrupt folder holds BSR state; cleaned on startup/shutdown; purge keeps last 10 (repeater) or 50 (normal) on auto-purge.
- UI: **FIX**, **BSR**, Fast BSR (last file), Del BSR / Del ALL / Keep 10, Replay RX, Resend File.
- `run.dll`: `SetBSRPath`, `SetRXCorruptSavePath`, segment APIs; `rscoder.dll`: `SetRsBSRPath`.
- Old BSR required **TX mode = RX mode**.
- Repeaters: all repeaters may answer BSRs even when “specific repeater only” is set.

### 5.4 Hybrid (Jul 2013 → Jan 2014)

- Check **HYBRID TX** → file uploaded → short over-air retrieval → peers download full file (exact resolution; not DRM-compressed image).
- Suggested RF params for the short code: **Mode E, QAM 4, Lead-in 12**.
- User Defined Server; password encrypted; special web directory optional; creates `HybridFiles`, `OnlineCallsigns`, `RxOkNotifications`.
- RX OK notifications sensed ~30 s after TX.
- Movies via **Mov** tab when Hybrid TX enabled; saved under `\Movies\`.
- EmbedTxt / some TX popup features disabled during Hybrid TX.
- Drag-drop from Explorer when Hybrid TX + TX tab (Jan 2014).

### 5.5 Repeater

Large **Rptr** menu (see §8): activate base repeater / beacon, interrogate, directories (files / weather VK-only / email), internet-via-repeater URL fetch, remote shutdown/restart/soft reboot, common repeater directory, repeat-back (must re-tick each time; defaults OFF after TX), SNR+audio level in replies, etc. Sysops and users must version-match for directory formats.

---

## 6. DRM default parameters

From **Quick Select TxMode** and encode menus in `Language.english`:

| Parameter | Default / recommended | UI evidence |
|-----------|----------------------|-------------|
| **Mode** | **B** | `SetDefaultTXmode1` = `B/2.4/HI/16/24`; radios A/B/E |
| **Bandwidth** | **2.4** kHz | Same quick-select string |
| **Protection** | **HI** | Quick-select middle token (vs LO for “perfect condx”) |
| **QAM** | **16** | Quick-select; radios 4 / 16 / 64 |
| **Trailing profile number** | **24** | Interpreted as **Lead-in** (secs/units); Hybrid docs set Lead-in **12** for short Hybrid bursts |
| **RS / ErrFix** | **RS2 – Light Encode** | `Mediumlightenc1` = “RS2 - Light Encode”; label shows RS4 as heavy option |
| **Picture downsize** | Default max **640×480** | `DEFAULTmax6404801` |
| **Repeat Header** | Always ON (recommended) | Setup menu |
| **BSR** | Automatic | Setup menu |

Other quick profiles (for docs / presets):

| Profile | String | Use |
|---------|--------|-----|
| Perfect / fastest | `A/2.4/LO/64/12` | Not recommended for HF |
| Excellent HF (≥20 m) | `B/2.4/HI/64/24` | Good conditions |
| Bad multipath | `E/2.4/HI/4/24` | Slowest; 80 m night |
| Hybrid short code tip | Mode **E**, QAM **4**, Lead-in **12** | Poor RF; tiny payload |

---

## 7. DLL dependencies and `hamdrm.dll` status

### 7.1 Present beside `EasyPal.exe`

| DLL | Role |
|-----|------|
| **`run.dll`** | Primary modem/runtime: `GetFAC`, `GetMSC`-class APIs via related exports, `GetSNR`, `GetParams`, `ControlRX`, `ResetRX`, `StartThreadTX`, `WriteTX`/`ReadRX`, `SetFileTX`, `SetBSRPath`, `SetRXCorruptSavePath`, `SetPTT`, `SetStartDelay`, audio device helpers, etc. |
| **`rscoder.dll`** | Reed–Solomon: `encode_rs`, `decode_rs`, `init_rscoder`, `SetRsBSRPath` |
| **`inpout32.dll`** | Parallel port PTT |

### 7.2 Roaming / plugins

| File | Role |
|------|------|
| `plugins\JPEG2000.dll` | JP2 support |
| Assorted `.exe` helpers | FTP, zip, IrfanView launcher, webcam — not core DRM |

### 7.3 `hamdrm.dll` search result

Searched recursively under:

- `C:\Program Files`
- `C:\Program Files (x86)`
- `C:\Windows\System32`
- `C:\Windows\SysWOW64`
- `C:\Users\shane\AppData` (Roaming + Local, including EasyPal tree)

**Result: `hamdrm.dll` — NOT FOUND**

Notes:

- `EasyPal.exe` about/credit string still mentions **“HAMDRM.DLL”** (Francesco Lanza **HB9TLK**).
- Changelog (14 Nov 2008) warns: *“DO NOT COPY HAMDRM.DLL INTO THE EASYPAL FOLDER”* / wrong version breaks EasyPal; registry/multi-install issues can produce “cannot find hamdrm.dll”.
- On this **Oct 2014** install, DRM functionality is provided by **`run.dll` + `rscoder.dll`**, not a standalone `hamdrm.dll` file on disk.

### 7.4 EasyPal-Next native stack (contrast)

| Next dependency | Role |
|-----------------|------|
| `libcodec2.dll` | FreeDV DATAC3/DATAC4/FSK_LDPC |
| Python `zfec` | Application-layer FEC |
| PortAudio / sounddevice | Audio I/O |

**Wire interop with original EasyPal requires either loading/reimplementing the DRM stack (`run.dll` semantics) or a clean-room modem that matches EasyPal on-air framing — Codec2 DATAC3 alone is not sufficient.**

---

## 8. `Language.english` menu / button map (thorough)

Language file header: `LANGUAGE FILE  Ver:29B/JAN/2014`.

### 8.1 Setup

| Control | Caption |
|---------|---------|
| Setup | Setup |
| Use Windows OpenDialog | Use Windows OpenDialog |
| Setup c/s-soundcard-PTT | Setup c/s-soundcard-PTT |
| Callsign / Soundcard | Callsign; Soundcard |
| CommPort PTT | Use CommPort (PTT rts/dtr) |
| CommPort CAT | Use CommPort (PTT CAT) |
| Parallel Port PTT | Use Parallel Port PTT |
| VOX | VOX |
| Max stability | Set MAX stability (if necessary) |
| Picture Downsize (TX) | HIRES 320×256 → unlimited (no resize) |
| Encode Options | RS1 Very Light → RS4 Heavy |
| Disable Options | Fullscreen click, RX/TX text, alerts, transitions |
| Unattended | Unattended (no popups to halt program) |
| BASIC Mode | BASIC Mode |
| RX/TX Volume | XP default soundcard only |
| BSR Mode | Automatic (recommended) / User Select (advanced) |
| Repeat Header | Highly recommended Always ON |
| Tag RX File | Callsign/Time/Mode |
| Progressive RX Picture | Not for RS files |
| Replay RX Exactly | Replay RX Exactly |
| GUI | Form color, text color, image, Add TX Text colors |
| WaterFall Options | Waterfall options submenu |
| Full Screen / Auto RX actual size | Laptop fullscreen; no resize RX |
| TX mode = RX mode | With old BSR |
| Define Additional Save Directory | Extra save path |
| Define IrfanView Directory | IrfanView integration |
| Make Language File / LANGUAGE | English + Chinese, Danish, Dutch, French, German, Italian, Japanese, Polish, Portuguese, Russian, Spanish, User Defined |
| Hybrid submenu | HYBRID, User Defined Server, TX with received server, Do NOT Upload Hybrid Pics, Ignore Hybrid Pics in normal mode |

### 8.2 Action

| Caption | Notes |
|---------|-------|
| CHAT | Dedicated chat UI |
| Load Webcam Picture | Webcam |
| Send Text / Show RX Text / Add TX Text | Text overlays & messaging |
| Send Form | Default, ICS213 (ARES), ICS213, ICS213-1, MARS |
| Session Log / Station Log | Logging |
| Tune | Calibration TX |
| CW ID | Morse ID |
| Purge excess files / Auto-Purge on shutdown | Disk hygiene |
| Run Defined Program 1–6 / Assign | External tools |
| Load support programs | EZCalls, EZLog, SstvPics, Digi-Sites; ReAssign directories |
| USE Repeater / USE FTP | Feature gates |
| Activate TX Waterfall | Risky; see §5 |
| Set TX multiple Instances | Multi-instance |
| Quick Select TxMode | B/… default + A/E presets (§6) |
| Full Screen / Print Text / Print Picture | Display & print |
| Twain Select / Acquire | Scanner |
| Send to / Grab from IrfanView | External editor |
| TX Screen / RX Screen | Pane focus |
| CAT Commands | Rig command panel |
| Troubleshooter | Diagnostics |

### 8.3 Main toolbar / pic actions (selected)

| Caption | Role |
|---------|------|
| LoadPic / LoadAny | Image vs any file |
| Copy / Paste | Clipboard |
| WFPic / WFTxt | Waterfall picture / text |
| Rptr | Repeater menu root |
| TRANSMIT | Primary TX toggle |
| FIX / BSR / Replay RX / Restart | Repair & replay |
| EmbedTxt | Embedded text on pic |
| TUNE / Session / Send Text / ID | Ops buttons |
| Pic/QSL / Save W/F / Station Log / WAV | Compose & logs |
| TX Now / ABORT (legacy string still in file) | TX control |
| begin.wav / end.wav setters | Cue WAV assignment |
| Fast BSR / Send Selected Request | BSR UI |
| FTP ON/OFF / To Web / >>Rptr / >>TX | Routing |

### 8.4 Rptr (Repeater) menu

Show Last Received Repeater Directory; Show Repeater LOG; save to `\Repeater\`; Start WebCam; Repeat back immediately; Interrogate Specific / Interrogate; View Repeater / Weather / Email directories; Replay last picture; Repeat Text in Waterfall; Request Hamcam; Request Repeater resend BSR; List Recent Activity; Remote control (Shutdown/Restart Repeater, Beacon, Soft Reboot); Send Alert Beep; Request Repeater Log; Internet Access; Use Common Repeater Directory; Send Email; Wait TX while QRM; Activate Repeater Beacon; Activate as Base Repeater.

### 8.5 FTP / Internet

Allow FTP Auto-Upload; Tag FTP uploads; Show FTP Upload List; ONAIR status + comments + See who is ONAIR; Banned callsigns; Do not allow my TX pics on web; Detect remote RX decode then stop TX (RS only); WRITE TXT for FTP; View/Delete pictures & messages on website; First Use clear pics/messages; Force FTP Upload / as TX1.jpg / Auto Force.

### 8.6 Status / DRM labels (GUI)

LeadIn, QAM, ErrFix, Width, Mode, Lng, TX, RX, remaining segments, MSC, FAC, Frame, Time, IO, SNR, Sync, Carrier Amplitudes, Carrier Sync Lock, OK Segs, Total, Position, dB, Hz markers 500–2500.

### 8.7 Checkboxes / radios of note

- Send in WFall as picture; Send as data file; RS2 encode data file; Send random Pics; WebCam only; AGC; Reverse; Negative; Active Mode (not recommended); Attach TX FILE.
- Modes **A/B/E**; QAM **4/16/64**; sizes 160×120 … 800×600.
- Auto-abort TX on first remote success vs list calls and manual abort.

---

## 9. Recommended next steps for interop

1. **Treat `run.dll` + `rscoder.dll` as the DRM ABI** — document exports, call order for RX listen / TX file / BSR paths; do **not** expect `hamdrm.dll` on modern EasyPal trees.
2. **P0 spike:** Always-on RX using the same FAC/MSC lock semantics; verify Mode **B / QAM 16 / RS2 / lead-in 24** against a stock EasyPal peer.
3. **Capture golden vectors:** WAV IQ/audio of EasyPal TX (default profile + BSR request + Hybrid short code) for regression tests in EasyPal-Next.
4. **Corrupt/BSR path parity:** Mirror `%APPDATA%\EasyPal\Corrupt` semantics so original EasyPal can repair Next TX and vice versa.
5. **Decide strategy:** (A) ctypes-wrap `run.dll` on Windows for compatibility mode, or (B) clean-room DRM compatible modem — DATAC3 remains “Next-native” parallel path.
6. **Default UX:** On-air profile → auto RX on, loopback off, waterfall live, Wait-for-QRM equivalent, Repeat Header on.
7. **P1 Hybrid:** Finish `HYBRID_REF` + community server dirs compatible with vk4aes-era layout / user-defined FTP.
8. **Defer P2** repeater/weather/ONAIR until wire TX/RX + BSR are solid.
9. **Legal/tech note:** `run.dll` is closed binary; wrapping may be pragmatic for interop builds, but long-term maintenance needs an open reimplementation.
10. **Keep path mapping** in §2 so users can migrate Inbox/Corrupt/Sent from Roaming EasyPal into EasyPal-Next folders without losing BSR state mid-experiment.

---

## 10. Source inventory (this mining pass)

| Source | Path |
|--------|------|
| Language map | `%APPDATA%\EasyPal\misc\Language.english` |
| Changelog | `%APPDATA%\EasyPal\misc\updateinfo.text` (07 OCT 2014 … older history) |
| Install tree | `C:\Program Files\EasyPal\` |
| User data tree | `%APPDATA%\EasyPal\` |
| `hamdrm.dll` | **NOT FOUND** (see §7.3) |

---

*Document generated for EasyPal-Next from the original EasyPal Windows install. Original EasyPal © Erik Sundstrup (VK4AES / VK4ESK, SK) and contributors; DRM heritage credited to HB9TLK HamDRM.*

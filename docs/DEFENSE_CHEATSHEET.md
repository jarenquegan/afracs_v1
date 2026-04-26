# AFRACS — Defense Day Cheat Sheet (Dev Side)

A plain-English walkthrough of how the system actually works under the hood.
Written for the 4-student client team to explain confidently during the panel defense.

---

## 1. The 30-Second Pitch

**AFRACS = Automated Facial Recognition Access Control System** for the
College of Health equipment cabinets.

- A camera watches the cabinet area.
- When a faculty member's face matches an enrolled record, the cabinet
  unlocks via a GPIO signal to a magnetic / electronic lock.
- Every attempt — granted or denied — is logged with timestamp + person + cabinet.
- After **5 consecutive failed attempts**, the system fires an **ALERT** state.
- A web admin dashboard handles faculty enrollment, cabinet management, and
  log review.

---

## 2. Architecture in One Diagram (mental model)

```
            ┌─────────────────────┐
            │   USB / Pi Camera   │
            └──────────┬──────────┘
                       │ (OpenCV VideoCapture)
                       ▼
        ┌──────────────────────────────┐
        │        FaceEngine            │
        │  YuNet (detect)              │
        │  SFace (encode + match)      │
        └──────────┬───────────────────┘
                   │
                   ▼
        ┌──────────────────────────────┐
        │  CabinetWindow (PyQt6)       │
        │  State machine:              │
        │  SLEEP → DETECTING →         │
        │  GRANTED / DENIED / ALERT    │
        └──────┬─────────────┬─────────┘
               │             │
               ▼             ▼
        ┌──────────┐   ┌──────────────┐
        │  MySQL   │   │  GPIO (lock) │
        │  afracs  │   │  via gpiozero│
        └────┬─────┘   └──────────────┘
             │
             ▼
        ┌──────────────────────────────┐
        │  Flask Admin Dashboard       │
        │  (browser, local network)    │
        └──────────────────────────────┘
```

**Two apps, one database.** The cabinet UI and the dashboard are independent
processes; they only talk to each other through the shared MySQL DB.

---

## 3. The Tech Stack (and *why* each piece)

| Layer            | Choice                              | Why this and not something else                                                         |
|------------------|-------------------------------------|-----------------------------------------------------------------------------------------|
| Language         | Python 3.11                         | Matches Raspberry Pi OS Bookworm default. Same code runs on dev laptop and on the Pi.   |
| Face detect      | **YuNet** (ONNX)                    | Tiny, fast CNN. Runs realtime even on a Pi 4 without a GPU.                             |
| Face recognize   | **SFace** (ONNX)                    | Produces a 128-D embedding (vector) per face. We store this, not the photo.             |
| Computer vision  | `opencv-contrib-python`             | Has the DNN module that loads YuNet + SFace. We avoid `dlib`/`face_recognition` because their build is broken on macOS arm64. |
| GUI              | PyQt6                               | True-fullscreen kiosk app. Touch-friendly. Looks the same on the Pi 7" screen.          |
| Database         | MySQL / MariaDB via PyMySQL         | Pure-Python driver — no compilation. MariaDB ships with Pi OS.                          |
| Web admin        | Flask 3                             | Lightweight, no SPA build step, runs offline on the local network.                      |
| Lock control     | `gpiozero` + `lgpio`                | Cross-platform abstraction. We can develop on macOS using `GPIOZERO_PIN_FACTORY=mock`.  |

> **Defense one-liner:** "Walang internet needed sa cabinet — fully offline.
> The dashboard is web-based pero local network only, walang public exposure."

---

## 4. How a Faculty Face Gets Saved (the part people will ask about)

This is the question the panel will hammer on. Memorize this flow.

### Step-by-step (admin dashboard route)

1. **Admin opens** `http://localhost:5000` and logs in.
2. Goes to **Faculty → Add** and fills in:
   - ID number (unique)
   - Full name
   - Position, Department
   - Tickbox which **cabinets** they can access (A / B / C / D)
3. Captures a photo using the **webcam capture** widget OR uploads one.
4. Clicks **Save**.

### What happens in the code (`dashboard.py` → `afracs/db.py`)

```
Browser captures photo  ──►  base64 string in form field "face_data"
                              │
                              ▼
            dashboard._extract_face_from_form()
                              │
                              ▼
            FaceEngine.encode_from_image(img)
                              │
                              ├── YuNet detects the face bbox
                              ├── SFace alignCrop() → normalized face
                              └── SFace feature() → 128-D float32 vector
                              │
                              ▼
            encoding_bytes = feat.tobytes()   # 128 × 4 = 512 bytes
                              │
                              ▼
            db.save_faculty(...) inserts row in `faculty` table
            with `encoding` column storing the BLOB
```

**Important point for the panel:**
We **never store the actual photo**. We only store the **mathematical embedding**
(a 128-number fingerprint of the face). It's:
- Privacy-friendly — you can't reconstruct the photo from the embedding.
- Tiny — 512 bytes per faculty.
- Fast to compare — matching is just a cosine similarity calculation.

### Re-enrollment / Edit

Going to **Faculty → Edit → "Re-enroll face"** uploads a new photo, runs the same
pipeline, and overwrites the `encoding` column via `db.update_faculty_encoding()`.

### Cabinet-side enrollment (alternative)

There's also a CLI fallback `python -m afracs.enroll` that captures multiple
samples from the live camera. Used during initial deployment before the
dashboard is up.

---

## 5. How Recognition Works at the Cabinet

State machine inside `afracs/ui/cabinet_window.py`:

```
SLEEP ──tap "Tap to begin"──► DETECTING
                                 │
                                 ├── live camera feed at ~30 fps
                                 ├── runs FaceEngine every 3rd frame
                                 │   (saves CPU on the Pi)
                                 │
                  ┌──────────────┼──────────────┐
                  │              │              │
              MATCHED        NOT MATCHED      NO FACE
        (5 consecutive   (90 consecutive    → keep waiting
         frames same       frames)
         person, score
         ≥ 0.363)
                  │              │
                  ▼              ▼
         has 1 cabinet?      DENIED state
         ├ yes → GRANTED      (counts as 1 failed attempt)
         └ no  → SELECTING    │
                              ▼
                       5+ failures? → ALERT state
```

### Key constants (in `afracs/config.py`)

| Constant                       | Default | Meaning                                                          |
|--------------------------------|---------|------------------------------------------------------------------|
| `RECOGNITION_THRESHOLD`        | 0.363   | SFace paper baseline cosine similarity. Below = unknown.         |
| `RECOGNITION_STREAK`           | 5       | Same person must match 5 frames in a row before granting.        |
| `UNRECOGNISED_DENY_FRAMES`     | 90      | ~3 seconds of "unknown face" before denial fires.                |
| `ALERT_AFTER_FAILED_ATTEMPTS`  | 5       | Triggers ALERT page (deliverable #5).                            |
| `LOCK_PULSE_SECONDS`           | 1.5     | How long the GPIO pin stays HIGH to release the lock.            |

> **Why a streak instead of one frame?**
> Single-frame matching is jittery and false-matches under bad lighting.
> Requiring 5 consecutive matches dramatically cuts impostor risk and only
> adds ~0.5 seconds to a legitimate unlock.

---

## 6. The Database Schema (`afracs/db.py`)

5 tables, all InnoDB, all UTF-8.

### `admins`
Dashboard logins. Seeded with one default admin on first init
(username/password from `.env`).

### `cabinets`
The 4 cabinets (A, B, C, D) — auto-seeded on init.

| column      | type         | notes                          |
|-------------|--------------|--------------------------------|
| id          | INT PK       | internal                       |
| cabinet_id  | VARCHAR(50)  | unique label (A, B, C, D)      |
| description | VARCHAR(255) |                                |
| location    | VARCHAR(255) |                                |

### `faculty`
| column     | type         | notes                                        |
|------------|--------------|----------------------------------------------|
| id         | INT PK       |                                              |
| id_number  | VARCHAR(50)  | unique faculty ID                            |
| name       | VARCHAR(255) |                                              |
| position   | VARCHAR(255) |                                              |
| department | VARCHAR(255) |                                              |
| **encoding** | **BLOB**   | **The 128-D SFace vector. NULL until enrolled.** |
| created_at | DATETIME     |                                              |

### `faculty_cabinet_access` (junction table — **why?**)
Many-to-many: one faculty can access many cabinets, one cabinet can be
accessed by many faculty. Without this table we'd have to repeat data.
ON DELETE CASCADE keeps it tidy if a cabinet or faculty is removed.

### `access_logs` (the audit trail — deliverable #6)
| column     | type                            | notes                                            |
|------------|---------------------------------|--------------------------------------------------|
| id         | INT PK                          |                                                  |
| faculty_id | INT NULL                        | NULL if denied user is unknown                   |
| cabinet_id | INT                             | which cabinet was attempted                      |
| status     | ENUM('granted','denied')        |                                                  |
| timestamp  | DATETIME                        | auto                                             |
| note       | TEXT                            | e.g. `"confidence=0.215"` or `"Cabinet A"`       |

> Every grant, deny, and alert event passes through `db.log_access(...)`.

---

## 7. The 8 Contract Deliverables — Where They Live

| #   | Deliverable                          | Lives in                                                            |
|-----|--------------------------------------|---------------------------------------------------------------------|
| 1   | Camera integration                   | `cabinet_window._open_camera()` (cv2.VideoCapture + QTimer @30fps)  |
| 2   | Face registration for faculty        | `dashboard.py` Faculty Add/Edit/Enroll routes + `FaceEngine.encode_from_image` |
| 3   | Real-time recognition                | `recognition.FaceEngine.process_frame` + `_handle_recognition`      |
| 4   | GPIO lock/unlock + grant/deny UI     | `hardware.CabinetLockBank` (pulses) + `GrantedPage` / `DeniedPage`  |
| 5   | Alert after 5 failed attempts        | `_after_denied` → `ALERT` state in `cabinet_window`                 |
| 6   | Access logging w/ full audit trail   | `db.log_access` + `access_logs` table + `/logs` dashboard route     |
| 7   | PyQt6 cabinet UI                     | `afracs/ui/cabinet_window.py` and `afracs/ui/pages/`                |
| 8   | Flask admin dashboard                | `dashboard.py` + `templates/`                                       |

---

## 8. Defense Q&A — Likely Questions and Crisp Answers

**Q: Why store an embedding instead of the photo itself?**
> Privacy and speed. The 128-D vector cannot be reverse-engineered into a
> face image, it's only 512 bytes per person, and matching is just a vector
> dot product — fast enough to run every frame on the Pi.

**Q: What if someone shows a printed photo to fool the system?**
> Honest answer: this is a single-camera 2D recognition system, not liveness
> detection. Liveness was not in the contracted scope. Mitigations we *do*
> have: the 5-frame streak (a static photo does pass this, so we acknowledge
> it as a known limitation), and the audit log + alert state for repeated
> abuse. If the client wants liveness later, that's a paid change order.

**Q: What happens if MySQL crashes mid-operation?**
> The cabinet UI catches DB exceptions and continues running offline; it
> just can't grant access until the DB is back. The lock stays secure by
> default — we fail closed, never fail open.

**Q: Why MariaDB and not SQLite?**
> SQLite would have worked for a single-cabinet deployment. We chose MariaDB
> because (a) it's what Pi OS Bookworm ships natively, (b) the contract
> describes a system that could scale to multiple cabinets, and (c) the
> dashboard runs as a separate process that needs concurrent DB access.

**Q: What's the recognition threshold based on?**
> 0.363 cosine similarity — that's the published SFace paper baseline for
> equal error rate. We can lower it for a more lenient match (more false
> grants) or raise it for stricter (more false denies). It's a config knob,
> not a magic number.

**Q: Is the dashboard exposed to the internet?**
> No. `FLASK_HOST=0.0.0.0` only binds it to all *local* interfaces. It's
> reachable from any device on the same LAN/Wi-Fi, never from outside. No
> port forwarding configured.

**Q: How fast is recognition?**
> ~30 fps capture, recognition runs every 3rd frame (~10 inferences/sec).
> Typical end-to-end "face appears → cabinet unlocks" is ~1 second after
> the 5-frame streak is hit.

**Q: How is the admin password stored?**
> Hashed with `werkzeug.security.generate_password_hash` (PBKDF2-SHA256
> by default). Plain text password is never stored.

---

## 9. Useful Demo Tricks (kapag nag-stuck si camera or recognition)

While running the cabinet UI, these keyboard shortcuts work:

| Key      | Effect                                   |
|----------|------------------------------------------|
| `T`      | Wake from SLEEP into DETECTING           |
| `G`      | Force GRANTED screen (demo Dr. Cruz)     |
| `D`      | Force DENIED screen                      |
| `A`      | Force ALERT screen                       |
| `S` / Esc| Back to SLEEP                            |
| `L`      | Toggle the lock indicator                |
| `F11`    | Toggle fullscreen / kiosk mode           |

> **Tip for defense:** Kung pumalpak yung camera, just press `G` and explain
> the granted flow verbally. Then press `D` five times to demo the alert.

---

## 10. File Map (where to look for what)

```
AFRACS/
├── cabinet.py                  ← entrypoint #1: PyQt6 cabinet UI
├── dashboard.py                ← entrypoint #2: Flask admin
├── setup.bat / run.bat         ← Windows installer + launcher
├── .env                        ← all config knobs (camera idx, DB, GPIO pin)
├── models/                     ← YuNet + SFace ONNX files
├── afracs/
│   ├── config.py               ← reads .env
│   ├── db.py                   ← schema + CRUD helpers (THIS file is gold)
│   ├── recognition.py          ← FaceEngine (detect → align → encode → match)
│   ├── hardware.py             ← CabinetLock GPIO pulser
│   ├── enroll.py               ← CLI enrollment fallback
│   ├── download_models.py      ← fetches the ONNX files
│   ├── theme.py                ← Maroon + Gold palette tokens
│   └── ui/
│       ├── cabinet_window.py   ← state machine (SLEEP/DETECTING/GRANTED/...)
│       ├── pages/              ← one widget per state
│       ├── styles.py           ← QSS stylesheet
│       └── header_bar.py / status_bar.py
└── templates/                  ← Flask Jinja templates for the dashboard
```

---

## 11. The "If Things Break" Mini-Guide

| Symptom                                | Likely cause                                        | Quick fix                                                |
|----------------------------------------|-----------------------------------------------------|----------------------------------------------------------|
| Dashboard won't start                  | MySQL not running                                   | Start MariaDB service; check `.env` MYSQL_USER/PASSWORD  |
| Cabinet UI: black camera               | Wrong camera index                                  | Set `CAMERA_INDEX=1` (or 2) in `.env`                    |
| "YuNet model not found"                | Forgot to download models                          | `python -m afracs.download_models`                        |
| GPIO error on Windows / macOS          | `gpiozero` trying to use real Pi pins               | `set GPIOZERO_PIN_FACTORY=mock` (already in run.bat)     |
| "No face detected" during enrollment   | Bad lighting, glasses glare, face too small        | Move closer, brighter light, retake photo                |
| Recognized but wrong person            | Threshold too lenient                               | Raise `RECOGNITION_THRESHOLD` in `.env` to e.g. 0.42     |
| Real person not recognized             | Threshold too strict                                | Lower `RECOGNITION_THRESHOLD` to e.g. 0.30, or re-enroll |

---

## 12. One-Sentence Summaries (memorize these)

- **"The system stores a 512-byte mathematical fingerprint of each faculty's face, never the photo itself."**
- **"The cabinet runs fully offline — no internet required."**
- **"Every access attempt is logged with user, cabinet, status, and timestamp — that's our full audit trail."**
- **"After 5 failed attempts, the system fires an alert state — that's deliverable #5."**
- **"The lock is fail-secure — kapag may problema, hindi siya bumubukas; nakakandado siya by default."**

Good luck. You got this.

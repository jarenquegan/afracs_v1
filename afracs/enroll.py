"""Faculty face enrollment CLI: python -m afracs.enroll"""
from __future__ import annotations

import sys

import cv2
import numpy as np

from afracs import config, db
from afracs.recognition import FaceEngine


def _ask(prompt: str, default: str = "") -> str:
    value = input(f"{prompt} [{default}]: ").strip()
    return value or default


def _ask_multi_select(items: list[str], prompt: str = "Select items") -> list[str]:
    print(f"\n{prompt}:")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item}")

    response = input("Enter selection (comma-separated numbers, or 'all'): ").strip()
    if response.lower() == "all":
        return items
    if not response:
        return []

    try:
        indices = [int(x.strip()) - 1 for x in response.split(",")]
        return [items[i] for i in indices if 0 <= i < len(items)]
    except (ValueError, IndexError):
        print("Invalid selection. Using default (all).")
        return items


def enroll() -> None:
    print("\n=== AFRACS Faculty Enrollment ===\n")

    id_number = input("Faculty ID number: ").strip()
    if not id_number:
        print("ID number cannot be empty.")
        sys.exit(1)

    try:
        check_conn = db.connect()
        existing = db.get_faculty_by_id_number(check_conn, id_number)
        check_conn.close()
    except Exception as exc:
        print(f"ERROR: Could not query database: {exc}")
        sys.exit(1)

    reenroll_only = False
    faculty_id_existing: int | None = None

    if existing:
        print(f"\nFound existing record:")
        print(f"  Name:       {existing['name']}")
        print(f"  Position:   {existing['position']}")
        print(f"  Department: {existing['department']}")
        print(f"  Face:       {'Enrolled' if existing['has_face'] else 'Not enrolled'}")
        print(f"  Cabinets:   {', '.join(existing['cabinets']) or 'None'}")
        print()
        choice = input("(r) Re-enroll face only  (u) Update all details  (q) Quit [r]: ").strip().lower() or "r"
        if choice == "q":
            print("Aborted.")
            sys.exit(0)
        elif choice == "r":
            reenroll_only = True
            faculty_id_existing = existing["id"]
            name = existing["name"]
            position = existing["position"]
            department = existing["department"]
            selected_cabinets = existing["cabinets"]
            print(f"\nRe-enrolling face for {name}. No profile changes.")
        else:
            faculty_id_existing = existing["id"]
            name = input(f"Faculty name [{existing['name']}]: ").strip() or existing["name"]
            position = _ask("Position / Title", existing["position"] or "Faculty")
            department = _ask("Department", existing["department"] or "College of Health")
    else:
        name = input("Faculty name: ").strip()
        if not name:
            print("Name cannot be empty.")
            sys.exit(1)
        position = _ask("Position / Title", "Faculty")
        department = _ask("Department", "College of Health")

    if not reenroll_only:
        try:
            temp_conn = db.connect()
            cabinets = db.get_cabinets(temp_conn)
            temp_conn.close()
        except Exception as exc:
            print(f"ERROR: Could not load cabinets from DB: {exc}")
            sys.exit(1)

        if not cabinets:
            print("ERROR: No cabinets configured in the database.")
            sys.exit(1)

        cabinet_names = [c["cabinet_id"] for c in cabinets]
        selected_cabinets = _ask_multi_select(
            cabinet_names,
            "Available cabinets (select which ones this faculty can access)",
        )

    print(f"\n--- Summary ---")
    print(f"ID: {id_number}")
    print(f"Name: {name}")
    if not reenroll_only:
        print(f"Position: {position}")
        print(f"Department: {department}")
        print(f"Cabinets: {', '.join(selected_cabinets or ['None'])}")
    print(f"\nWill capture {config.ENROLL_SAMPLES} face samples. Press Q to abort.\n")

    try:
        engine = FaceEngine()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        print(f"ERROR: Cannot open camera index {config.CAMERA_INDEX}.")
        sys.exit(1)

    embeddings: list[np.ndarray] = []
    preview_name = f"Enrolling: {name}"
    cv2.namedWindow(preview_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(preview_name, 640, 480)

    print("Hold still and look at the camera …")

    while len(embeddings) < config.ENROLL_SAMPLES:
        ok, frame = cap.read()
        if not ok:
            continue

        h, w = frame.shape[:2]
        engine._detector.setInputSize((w, h))
        _, detections = engine._detector.detect(frame)

        status_text = f"Captured: {len(embeddings)}/{config.ENROLL_SAMPLES}"

        if detections is not None and len(detections) > 0:
            best = max(detections, key=lambda d: d[-1])
            try:
                aligned = engine._recognizer.alignCrop(frame, best)
                feat    = engine._recognizer.feature(aligned)
                embeddings.append(feat.copy())

                x, y, fw, fh = (int(v) for v in best[:4])
                cv2.rectangle(frame, (x, y), (x + fw, y + fh), (58, 200, 58), 2)
            except Exception:
                pass

        cv2.putText(
            frame, status_text,
            (16, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2,
        )
        cv2.imshow(preview_name, frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("\nAborted.")
            cap.release()
            cv2.destroyAllWindows()
            sys.exit(0)

    cap.release()
    cv2.destroyAllWindows()

    if len(embeddings) < 5:
        print(f"ERROR: Only captured {len(embeddings)} samples — need at least 5.")
        sys.exit(1)

    mean_embedding = np.mean(embeddings, axis=0).astype(np.float32)
    if mean_embedding.shape != (1, 128):
        mean_embedding = mean_embedding.reshape(1, 128)

    print(f"\nCaptured {len(embeddings)} samples. Saving to database …")

    try:
        conn = db.connect()
        if faculty_id_existing is not None:
            if not reenroll_only:
                db.update_faculty(
                    conn,
                    faculty_id=faculty_id_existing,
                    id_number=id_number,
                    name=name,
                    position=position,
                    department=department,
                    cabinet_ids=selected_cabinets,
                )
            db.update_faculty_encoding(conn, faculty_id_existing, mean_embedding.tobytes())
            conn.close()
            action = "re-enrolled" if reenroll_only else "updated"
            print(f"\nSuccess! {name} {action} (faculty id = {faculty_id_existing}).")
        else:
            faculty_id = db.save_faculty(
                conn,
                id_number=id_number,
                name=name,
                position=position,
                department=department,
                encoding_bytes=mean_embedding.tobytes(),
                cabinet_ids=selected_cabinets,
            )
            conn.close()
            print(f"\nSuccess! {name} enrolled (faculty id = {faculty_id}).")
    except Exception as exc:
        print(f"ERROR saving to DB: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    enroll()

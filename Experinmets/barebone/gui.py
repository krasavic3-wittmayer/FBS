"""Minimal desktop GUI for FBS.

Same two entry points as main.py's CLI menu — import an audio recording,
or run a random-outpost synthetic test — just clickable. Solving runs on a
background thread so the window doesn't freeze during the 10-25s solve.
"""

import random
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext

from audio_input import load_audio
from db import build_index, flash_arrays
from fingerprint import bin_events
from flash_detect import detect_flashes
from generate import generate_flashes, generate_storms
from main import pick_true_outpost
from physics import distance_km
from solver import estimate_outpost

AUDIO_FILETYPES = [
    ("Audio files", "*.wav *.mp3 *.mp4 *.webm *.m4a *.flac *.ogg *.mkv *.mov"),
    ("All files", "*.*"),
]


class App:
    def __init__(self, root):
        self.root = root
        root.title("FBS — Flash-Based outpost Solver")
        root.geometry("620x440")
        root.minsize(480, 320)

        frame = tk.Frame(root, padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="FBS", font=("", 18, "bold")).pack(anchor="w")
        tk.Label(frame, text="Localizes an outpost's position and recording time from thunder-arrival timing.").pack(anchor="w", pady=(0, 10))

        button_row = tk.Frame(frame)
        button_row.pack(fill="x", pady=(0, 8))
        self.import_button = tk.Button(button_row, text="Import Audio…", command=self.on_import_audio)
        self.import_button.pack(side="left", padx=(0, 8))
        self.random_button = tk.Button(button_row, text="Random Outpost (synthetic test)", command=self.on_random_outpost)
        self.random_button.pack(side="left")

        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(frame, textvariable=self.status_var, fg="#555").pack(anchor="w", pady=(0, 6))

        self.output = scrolledtext.ScrolledText(frame, height=16, state="disabled", font=("Courier", 10))
        self.output.pack(fill="both", expand=True)

    # -- UI helpers, always called from the main thread --

    def log(self, text):
        self.output.configure(state="normal")
        self.output.insert("end", text + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def set_busy(self, busy, message=""):
        state = "disabled" if busy else "normal"
        self.import_button.configure(state=state)
        self.random_button.configure(state=state)
        self.status_var.set(message if busy else "Ready.")

    def log_from_worker(self, text):
        self.root.after(0, self.log, text)

    def done_from_worker(self):
        self.root.after(0, self.set_busy, False, "")

    # -- Import audio --

    def on_import_audio(self):
        path = filedialog.askopenfilename(title="Select a recording", filetypes=AUDIO_FILETYPES)
        if not path:
            return
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")
        self.set_busy(True, "Solving…")
        threading.Thread(target=self._run_import_audio, args=(path,), daemon=True).start()

    def _run_import_audio(self, path):
        try:
            samples, sample_rate = load_audio(path)
            duration_s = len(samples) / sample_rate
            self.log_from_worker(f"Loaded: {path}")
            self.log_from_worker(f"duration={duration_s:.1f}s  sample_rate={sample_rate}Hz")

            times, amplitudes = detect_flashes(samples, sample_rate)
            self.log_from_worker(f"Detected {len(times)} flash events")
            if len(times) == 0:
                self.log_from_worker("No events detected — nothing to localize.")
                return

            recorded_fingerprint = bin_events(times, amplitudes, window_s=duration_s)

            # No real flash database wired up yet (lightningmaps.org
            # integration is still pending) — matches against a freshly
            # generated synthetic one, so results are illustrative only.
            self.log_from_worker("Generating reference flash data (synthetic — no real database wired up yet)…")
            storms = generate_storms(24 * 60, 5)
            storm_radius_km = random.uniform(5, 20)
            flashes = generate_flashes(storms, storm_radius_km)
            lat, lon, flash_time = flash_arrays(flashes)
            tree = build_index(lat, lon)

            self.log_from_worker("Solving (location + recording time, both unknown)…")
            calculated_outpost, calc_burst_start, calc_burst_end = estimate_outpost(
                lat, lon, flash_time, tree, recorded_fingerprint, duration_s=duration_s
            )

            if calculated_outpost is None:
                self.log_from_worker("Could not localize — no matching pattern found.")
                return

            self.log_from_worker(f"Predicted location: lat={calculated_outpost.lat:.4f}, lon={calculated_outpost.lon:.4f}")
            self.log_from_worker(f"Predicted recording window: {calc_burst_start:.1f}s – {calc_burst_end:.1f}s (arbitrary reference clock)")
        except Exception as exc:
            self.log_from_worker(f"Error: {exc}")
        finally:
            self.done_from_worker()

    # -- Random outpost (synthetic self-test) --

    def on_random_outpost(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")
        self.set_busy(True, "Simulating + solving…")
        threading.Thread(target=self._run_random_outpost, daemon=True).start()

    def _run_random_outpost(self):
        try:
            seed = random.randrange(2**32)
            random.seed(seed)
            self.log_from_worker(f"seed={seed}")

            storms = generate_storms(24 * 60, 5)
            storm_radius_km = random.uniform(5, 20)
            flashes = generate_flashes(storms, storm_radius_km)
            lat, lon, flash_time = flash_arrays(flashes)
            tree = build_index(lat, lon)

            true_outpost, recorded_fingerprint, true_burst_start, true_burst_end = pick_true_outpost(
                lat, lon, flash_time, tree, flashes
            )
            self.log_from_worker(f"{len(flashes)} flashes generated from {len(storms)} storms")

            calculated_outpost, calc_burst_start, calc_burst_end = estimate_outpost(
                lat, lon, flash_time, tree, recorded_fingerprint
            )

            error_km = distance_km(true_outpost.lat, true_outpost.lon, calculated_outpost.lat, calculated_outpost.lon)
            time_error_s = abs(calc_burst_start - true_burst_start)

            self.log_from_worker(f"True outpost:      lat={true_outpost.lat:.4f}, lon={true_outpost.lon:.4f}, burst=({true_burst_start:.1f}s,{true_burst_end:.1f}s)")
            self.log_from_worker(f"Predicted outpost:  lat={calculated_outpost.lat:.4f}, lon={calculated_outpost.lon:.4f}, burst=({calc_burst_start:.1f}s,{calc_burst_end:.1f}s)")
            self.log_from_worker(f"Location error: {error_km:.2f} km")
            self.log_from_worker(f"Time error: {time_error_s:.1f} s")
        except Exception as exc:
            self.log_from_worker(f"Error: {exc}")
        finally:
            self.done_from_worker()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

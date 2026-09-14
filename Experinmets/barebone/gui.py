"""Desktop GUI for FBS.

Same two entry points as main.py's CLI menu — import an audio recording,
or run a random-outpost synthetic test. Solving runs on a background
thread so the window stays responsive. Adds a real-world map with a
similarity heatmap around the answer (see solver.score_region) and
markers for the predicted (and, in test mode, true) outpost.
"""

import random
import threading

import customtkinter as ctk
import tkintermapview

from audio_input import load_audio
from db import build_index, flash_arrays
from fingerprint import bin_events
from flash_detect import detect_flashes
from generate import generate_flashes, generate_storms
from main import pick_true_outpost
from physics import distance_km
from solver import estimate_outpost, score_region

AUDIO_FILETYPES = [
    ("Audio files", "*.wav *.mp3 *.mp4 *.webm *.m4a *.flac *.ogg *.mkv *.mov"),
    ("All files", "*.*"),
]

# Heatmap grid is deliberately lighter than the solver's own fine pass
# (step=0.02, radius=0.3 -> 961 cells) — this is purely for display, and
# that many canvas polygons redrawn on every pan/zoom gets sluggish.
HEATMAP_STEP_DEG = 0.02
HEATMAP_RADIUS_DEG = 0.15


def score_to_color(t):
    """Blue (low) -> yellow -> red (high), t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        u = t / 0.5
        r, g, b = 40 + u * (255 - 40), 70 + u * (220 - 70), 190 - u * 190
    else:
        u = (t - 0.5) / 0.5
        r, g, b = 255, 220 - u * (220 - 40), 0
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("FBS — Flash-Based Outpost Solver")
        self.geometry("1140x700")
        self.minsize(820, 480)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_map()

        self.heat_polygons = []
        self.markers = []

    # -- layout --

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nswe")
        sidebar.grid_rowconfigure(5, weight=1)
        sidebar.grid_propagate(False)

        ctk.CTkLabel(sidebar, text="FBS", font=ctk.CTkFont(size=28, weight="bold")).grid(
            row=0, column=0, padx=24, pady=(24, 2), sticky="w"
        )
        ctk.CTkLabel(
            sidebar,
            text="Localizes an outpost's position\nand recording time from\nthunder-arrival timing.",
            justify="left", text_color="gray65",
        ).grid(row=1, column=0, padx=24, pady=(0, 20), sticky="w")

        self.import_button = ctk.CTkButton(sidebar, text="Import Audio…", height=38, command=self.on_import_audio)
        self.import_button.grid(row=2, column=0, padx=24, pady=6, sticky="ew")

        self.random_button = ctk.CTkButton(
            sidebar, text="Random Outpost (test)", height=38, fg_color="transparent",
            border_width=2, text_color=("gray10", "gray90"), command=self.on_random_outpost,
        )
        self.random_button.grid(row=3, column=0, padx=24, pady=6, sticky="ew")

        self.status_var = ctk.StringVar(value="Ready.")
        ctk.CTkLabel(sidebar, textvariable=self.status_var, text_color="gray60", anchor="w").grid(
            row=4, column=0, padx=24, pady=(14, 6), sticky="ew"
        )

        self.output = ctk.CTkTextbox(sidebar, font=("Courier", 11), corner_radius=8)
        self.output.grid(row=5, column=0, padx=24, pady=(0, 24), sticky="nswe")
        self.output.configure(state="disabled")

    def _build_map(self):
        self.map_widget = tkintermapview.TkinterMapView(self, corner_radius=0)
        self.map_widget.grid(row=0, column=1, sticky="nswe")
        self.map_widget.set_position(0, 0)
        self.map_widget.set_zoom(3)

    # -- UI helpers, always called from the main thread --

    def log(self, text):
        self.output.configure(state="normal")
        self.output.insert("end", text + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def clear_output(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def set_busy(self, busy, message=""):
        state = "disabled" if busy else "normal"
        self.import_button.configure(state=state)
        self.random_button.configure(state=state)
        self.status_var.set(message if busy else "Ready.")

    def log_from_worker(self, text):
        self.after(0, self.log, text)

    def done_from_worker(self):
        self.after(0, self.set_busy, False, "")

    def clear_map(self):
        for polygon in self.heat_polygons:
            polygon.delete()
        self.heat_polygons = []
        for marker in self.markers:
            marker.delete()
        self.markers = []

    def draw_heatmap(self, points):
        """points: list of (lat, lon, score). Called from the main thread."""
        scores = [s for _, _, s in points if s > -1.0]
        if not scores:
            return
        lo, hi = min(scores), max(scores)
        span = (hi - lo) or 1.0
        half = HEATMAP_STEP_DEG / 2

        for lat, lon, score in points:
            if score <= -1.0:
                continue
            normalized = (score - lo) / span
            corners = [(lat - half, lon - half), (lat - half, lon + half), (lat + half, lon + half), (lat + half, lon - half)]
            polygon = self.map_widget.set_polygon(corners, fill_color=score_to_color(normalized), outline_color=score_to_color(normalized), border_width=1)
            self.heat_polygons.append(polygon)

    def draw_marker(self, lat, lon, text, circle_color, outside_color):
        marker = self.map_widget.set_marker(lat, lon, text=text, marker_color_circle=circle_color, marker_color_outside=outside_color)
        self.markers.append(marker)

    def show_on_map_from_worker(self, points, markers):
        def _apply():
            self.clear_map()
            self.draw_heatmap(points)
            for lat, lon, text, circle_color, outside_color in markers:
                self.draw_marker(lat, lon, text, circle_color, outside_color)
            if markers:
                self.map_widget.set_position(markers[-1][0], markers[-1][1])
                self.map_widget.set_zoom(11)
        self.after(0, _apply)

    # -- Import audio --

    def on_import_audio(self):
        path = ctk.filedialog.askopenfilename(title="Select a recording", filetypes=AUDIO_FILETYPES)
        if not path:
            return
        self.clear_output()
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

            points = score_region(
                lat, lon, flash_time, tree, recorded_fingerprint, calculated_outpost,
                duration_s=duration_s, step=HEATMAP_STEP_DEG, radius=HEATMAP_RADIUS_DEG,
            )
            self.show_on_map_from_worker(points, [
                (calculated_outpost.lat, calculated_outpost.lon, "Predicted", "#ff5a36", "#8a1f0d"),
            ])
        except Exception as exc:
            self.log_from_worker(f"Error: {exc}")
        finally:
            self.done_from_worker()

    # -- Random outpost (synthetic self-test) --

    def on_random_outpost(self):
        self.clear_output()
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

            points = score_region(
                lat, lon, flash_time, tree, recorded_fingerprint, calculated_outpost,
                step=HEATMAP_STEP_DEG, radius=HEATMAP_RADIUS_DEG,
            )
            self.show_on_map_from_worker(points, [
                (true_outpost.lat, true_outpost.lon, "True", "#33cc66", "#116633"),
                (calculated_outpost.lat, calculated_outpost.lon, "Predicted", "#ff5a36", "#8a1f0d"),
            ])
        except Exception as exc:
            self.log_from_worker(f"Error: {exc}")
        finally:
            self.done_from_worker()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

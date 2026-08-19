# FBS — Find By Storm

FBS is an experimental system for locating an audio recording of a
thunderstorm using a global lightning strike dataset.

The goal is simple:

> Given an audio recording containing thunder and a dataset of lightning
> strikes, determine **where and when the recording was made**.

## How it works

FBS compares the acoustic fingerprint of a recording with patterns
formed by lightning strikes in the dataset.

The planned pipeline is roughly:

```text
Audio recording
      │
      ▼
Spectrogram
      │
      ▼
Acoustic fingerprint
      │
      ├─────────────────────┐
      │                     │
      ▼                     ▼
Lightning dataset      Candidate locations
      │                     │
      └──────────┬──────────┘
                 ▼
          Similarity search
                 │
                 ▼
          Estimated location
             + timestamp
```

The system uses the timing and relative strength of thunder events to
compare the recording against known lightning activity.

Current status

🚧 Experimental / Work in Progress

The project is currently focused on building a synthetic test environment
and validating the core algorithms.

Current components include:

 Lightning test-data generator
 Geographic distance calculation
 Filtering lightning strikes by distance
 30-minute recording window selection
 Synthetic lightning waveform generation
 Audio spectrogram generation
 Low-frequency audio fingerprinting
 Cosine similarity experiments
 Synthetic recording generation
 End-to-end localization
 Large-dataset optimization
 Spatial and temporal indexing
 GPU acceleration
 Real-world dataset testing
Test data

The project uses generated lightning data for development and testing.

Large generated datasets are intentionally not included in the repository.

They are stored locally under:

Data/

and are excluded using .gitignore.

The current test data can contain millions of synthetic lightning strikes
and is used to simulate large-scale lightning datasets.

Why?

The idea behind FBS is to investigate whether a thunderstorm recording can
be geographically localized by comparing its acoustic signature with
known lightning activity.

If successful, the system should be able to take something like:

recording.wav
lightning_dataset

and produce an estimate such as:

Latitude:  50.xxxx
Longitude: 14.xxxx
Time:      xx:xx:xx UTC

without being given the recording's location beforehand.

Technology

The project is currently written primarily in Python.

Main technologies and libraries:

Python
NumPy
SciPy
Matplotlib
WAV audio processing
Spectrogram analysis
Cosine similarity

Future versions may use:

SQLite / indexed data storage
GPU acceleration
Spatial indexing
Vectorized numerical processing
Development

Clone the repository and create a virtual environment:

git clone <repository-url>
cd FBS


python -m venv .venv
source .venv/bin/activate

Install dependencies:

pip install -r requirements.txt
Disclaimer

FBS is an experimental project.

The current datasets are synthetic and the localization algorithm is still
under development. Results from the current implementation should not be
considered accurate real-world lightning localization.
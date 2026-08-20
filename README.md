# FBS — Find By Storm

FBS is a research project about a simple but challenging question:

> Can a thunderstorm recording be used to infer where and when the storm was occurring?

The idea is to treat thunder as a signal that carries spatial and temporal information. A recording captured near a storm contains a pattern of delayed, attenuated, and overlapping thunder events. By modeling those events and comparing them to a dataset of lightning activity, the system aims to estimate the most likely location and time of the recording.

## What the project is about

This project explores the idea of acoustic storm localization.

Instead of using GPS or a known reference point, it asks whether thunder itself can act as a fingerprint. The system turns recorded thunder into a compact acoustic signature and compares it against synthetic or historical lightning data. If the matching pattern is strong enough, the storm's origin can be inferred from the data.

The broader goal is not just to detect thunder, but to reason about:

- where lightning was active relative to the recorder
- when thunder events occurred in sequence
- how signal strength decays with distance
- how a storm's acoustic footprint differs from location to location
- how to search large candidate datasets efficiently

## Core concept

Lightning produces a highly distinctive acoustic pattern. The sound arrives at a microphone over time because different strikes are at different distances and directions, and each event is shaped by propagation through the atmosphere.

FBS attempts to model this process in reverse:

```text
Thunder recording
      │
      ▼
Spectral fingerprint extraction
      │
      ▼
Comparison with lightning-event patterns
      │
      ▼
Candidate storm locations and times
      │
      ▼
Best-fit estimate
```

The project combines ideas from:

- signal processing
- acoustics
- geospatial modeling
- time-series matching
- probabilistic or similarity-based search

## Why this matters

Thunderstorm localization is useful in several contexts:

- understanding the geometry of a storm from a single recording
- estimating sensor placement from acoustic evidence
- studying atmospheric sound propagation
- building better systems for environmental monitoring
- exploring how much information is present in natural acoustic events

In other words, the project is less about audio classification and more about turning a natural sound into a spatial clue.

## Research direction

FBS is deliberately framed as a prototype and a scientific exploration, not a turnkey product. The project investigates how well thunder recordings can be matched to lightning data under controlled conditions, and it tests the assumptions behind the approach.

The work focuses on:

- generating realistic synthetic thunder and lightning scenarios
- building acoustic fingerprints from thunder-like signals
- comparing fingerprints against spatially distributed event data
- filtering candidate windows and locations over time
- scaling the search to larger datasets without losing the signal structure

## Typical workflow

A simplified version of the pipeline looks like this:

1. Create or load lightning event data.
2. Model a storm region and the distribution of flashes.
3. Generate thunder-like audio fingerprints from distances and timing.
4. Extract a compact acoustic representation from a recording.
5. Compare the fingerprint against likely lightning patterns.
6. Rank candidate locations and times by similarity.
7. Return the most plausible storm configuration.

This is not meant to be a generic sound-matching system; it is a domain-specific attempt to infer storm geometry from thunder.

## Repository intent

This repository is a place to explore that hypothesis in code. It contains experiments for:

- synthetic storm and flash generation
- lightning-event modeling
- waveform generation
- spectrogram and fingerprint extraction
- candidate filtering
- similarity testing
- data handling for larger geospatial datasets

The code is intentionally exploratory and aimed at validating the core idea, rather than serving as a finished application interface or a production-grade data pipeline.

## Status

This project is best understood as an early-stage research prototype. It is focused on testing the feasibility of the concept, experimenting with signal representations, and developing the matching logic that connects thunder recordings to storm activity.

## License

This project is distributed as-is for research and experimentation. See the repository license file if present for usage terms.

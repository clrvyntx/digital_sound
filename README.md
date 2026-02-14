# Sustain Synth

A real-time keyboard synthesizer built with **pygame-ce**, **NumPy**, and **SciPy**.

Hold keys on your keyboard to play sustained notes.  

## Features

-  Chromatic keyboard (A4 → C6)
-  Multiple waveforms: Sine, Square, Triangle
-  Real-time audio effects: Phaser, Echo, Chorus
-  Sustain notes while holding keys

---

# Installation (Using pygame-ce)

This project uses **pygame-ce**, the actively maintained Community Edition of pygame.

## Clone the Repository

```bash
git clone https://github.com/clrvyntx/sustain_synth
cd sustain-synth
```

## Create a Virtual Environment (Recommended)

### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```
## Install dependencies

```bash
pip install pygame-ce numpy scipy
```

# Running the Synth

```bash
python sustain_synth.py
```

import pygame
import numpy as np
from scipy import signal

# Audio settings
SAMPLE_RATE = 44100
VOLUME = 0.1
DURATION = 3.0  # Long enough for sustained note

# Initialize mixer and pygame
pygame.mixer.pre_init(SAMPLE_RATE, size=-16, channels=1)
pygame.init()

WIDTH, HEIGHT = 600, 350
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Sustain Synth - Hold keys to play")

# Calculate frequency for semitone offset relative to A4 = 440 Hz
def semitone_freq(base_freq=440.0, semitone_offset=0):
    return base_freq * 2 ** (semitone_offset / 12)

# Map keys to semitone offsets (chromatic scale from A4)
note_map = {
    pygame.K_a: 0,    # A4
    pygame.K_w: 1,    # A#4 / Bb4
    pygame.K_s: 2,    # B4
    pygame.K_e: 3,    # C5
    pygame.K_d: 4,    # C#5 / Db5
    pygame.K_f: 5,    # D5
    pygame.K_t: 6,    # D#5 / Eb5
    pygame.K_g: 7,    # E5
    pygame.K_y: 8,    # F5
    pygame.K_h: 9,    # F#5 / Gb5
    pygame.K_u: 10,   # G5
    pygame.K_j: 11,   # G#5 / Ab5
    pygame.K_k: 12,   # A5
    pygame.K_o: 13,   # A#5 / Bb5
    pygame.K_l: 14,   # B5
    pygame.K_p: 15,   # C6
}

# Supported waveforms
waveforms = ['sine', 'square', 'triangle']
current_waveform_idx = 0

# Effect toggles
phaser_on = False
echo_on = False
chorus_on = False

def apply_phaser(wave, sample_rate=44100, depth=0.001, rate=0.5):
    """
    Phaser effect:
    - Creates a time-varying delay using an LFO (Low Frequency Oscillator).
    - Mixes the delayed signal back with the original, creating a sweeping comb-filter sound.
    """

    max_delay_samples = depth * sample_rate  # Maximum delay in samples based on modulation depth
    n = len(wave)                            # Total number of samples in the wave
    t = np.arange(n)                        # Sample indices array for processing

    # LFO oscillates between 0 and 1 at given rate (Hz), shaping delay over time
    lfo = (1 + np.sin(2 * np.pi * rate * t / sample_rate)) / 2

    # Calculate variable delay in samples at each time point
    delay_samples = lfo * max_delay_samples

    # Calculate indices of delayed samples for interpolation (float indices)
    delayed_indices = t - delay_samples

    # Clamp indices to valid range to avoid indexing outside array bounds
    delayed_indices = np.clip(delayed_indices, 0, n - 1)

    # Interpolate wave values at fractional delayed indices (smooth delay)
    delayed_wave = np.interp(delayed_indices, t, wave)

    # Mix original wave (70%) with delayed wave (30%)
    output = 0.7 * wave + 0.3 * delayed_wave

    # Apply fade-in and fade-out at edges to smooth loop transitions and avoid clicks
    fade_duration_seconds = 0.01  # 10 milliseconds fade duration
    fade_samples = int(sample_rate * fade_duration_seconds)
    fade_in = np.linspace(0, 1, fade_samples)   # Linear fade-in curve
    fade_out = np.linspace(1, 0, fade_samples)  # Linear fade-out curve

    output[:fade_samples] *= fade_in      # Fade-in start of output
    output[-fade_samples:] *= fade_out    # Fade-out end of output

    return output.astype(np.float32)  # Return processed wave as float32 array


def apply_echo(wave, sample_rate=44100, delay_sec=0.15, decay=0.25):
    """
    Echo effect:
    - Adds a delayed, decayed copy of the signal back on top of the original.
    - Creates an echo or slapback delay.
    """

    delay_samples = int(delay_sec * sample_rate)  # Convert delay time (seconds) to samples

    # Create an output array larger than original wave to hold echo tail
    echo_wave = np.zeros(len(wave) + delay_samples)

    echo_wave[:len(wave)] = wave                 # Original wave copied to start
    echo_wave[delay_samples:] += decay * wave   # Add decayed delayed wave starting after delay

    # Return output trimmed to original length to keep consistent buffer size
    return echo_wave[:len(wave)].astype(np.float32)


def apply_chorus(wave, sample_rate=44100, depth=0.002, rate=1.5, voices=3):
    """
    Chorus effect:
    - Mixes multiple slightly delayed and pitch-modulated (detuned) copies of the wave.
    - Uses LFO to modulate delay time, producing subtle pitch variation.
    - Creates a thicker, richer sound as if multiple instruments play together.
    """

    n = len(wave)              # Number of samples in input wave
    t = np.arange(n)           # Sample indices array for processing

    output = np.copy(wave) * 0.5  # Start output with half-volume original wave

    for i in range(voices):
        # Create an LFO that modulates delay time for each voice with unique frequency
        lfo = depth * np.sin(2 * np.pi * rate * (i + 1) * t / sample_rate)

        # Calculate delayed sample indices by subtracting modulated delay (pitch shift)
        delayed_indices = t - (lfo * sample_rate).astype(int)

        # Clamp delayed indices within valid array range
        delayed_indices = np.clip(delayed_indices, 0, n - 1)

        # Interpolate wave values at fractional delayed indices for smooth modulation
        delayed_wave = np.interp(delayed_indices, t, wave)

        # Add each delayed wave scaled by number of voices to avoid clipping
        output += delayed_wave * (0.5 / voices)

    # Return the processed chorus effect wave
    return output.astype(np.float32)

def generate_waveform(wave_type, freq, duration=DURATION, sample_rate=SAMPLE_RATE, volume=VOLUME):
    periods = int(freq * duration)
    duration = periods / freq
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

    if wave_type == 'sine':
        wave = np.sin(2 * np.pi * freq * t)
    elif wave_type == 'square':
        wave = signal.square(2 * np.pi * freq * t)
    elif wave_type == 'triangle':
        wave = signal.sawtooth(2 * np.pi * freq * t, 0.5)
    else:
        raise ValueError("Invalid wave_type.")

    # Make square wave have lower volume
    if wave_type == 'square':
        wave *= 0.4

    # Apply effects in order
    if phaser_on:
        wave = apply_phaser(wave, sample_rate=sample_rate)
    if echo_on:
        wave = apply_echo(wave, sample_rate=sample_rate)
    if chorus_on:
        wave = apply_chorus(wave, sample_rate=sample_rate)

    wave = volume * wave

    audio = np.int16(wave * 32767)
    return audio

def regenerate_sounds():
    new_sounds = {}
    base_freq = 440.0
    for key, semitone_offset in note_map.items():
        freq = semitone_freq(base_freq, semitone_offset)
        audio = generate_waveform(waveforms[current_waveform_idx], freq)
        new_sounds[key] = pygame.sndarray.make_sound(audio)
    return new_sounds

sounds = regenerate_sounds()
playing_channels = {}

font = pygame.font.SysFont(None, 24)
instructions = [
    font.render("Hold keys A,W,S,E,D,F,T,G,Y,H,U,J,K,O,L,P to play notes.", True, (255, 255, 255)),
    font.render("Press 1: Sine  2: Square  3: Triangle", True, (255, 255, 255)),
    font.render("Press Z to toggle Phaser ON/OFF", True, (255, 255, 255)),
    font.render("Press X to toggle Echo ON/OFF", True, (255, 255, 255)),
    font.render("Press C to toggle Chorus ON/OFF", True, (255, 255, 255)),
]

def render_effect_status():
    return [
        font.render(f"Waveform: {waveforms[current_waveform_idx]}", True, (255, 255, 0)),
        font.render(f"Phaser: {'ON' if phaser_on else 'OFF'}", True, (0, 255, 0) if phaser_on else (255, 0, 0)),
        font.render(f"Echo: {'ON' if echo_on else 'OFF'}", True, (0, 255, 0) if echo_on else (255, 0, 0)),
        font.render(f"Chorus: {'ON' if chorus_on else 'OFF'}", True, (0, 255, 0) if chorus_on else (255, 0, 0)),
    ]

effect_status = render_effect_status()

running = True
while running:
    screen.fill((30, 30, 30))
    for i, line in enumerate(instructions):
        screen.blit(line, (10, 40 + i * 30))
    for i, status_line in enumerate(effect_status):
        screen.blit(status_line, (10, 200 + i * 30))
    pygame.display.flip()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_z:
                phaser_on = not phaser_on
                effect_status = render_effect_status()
                sounds = regenerate_sounds()

            elif event.key == pygame.K_x:
                echo_on = not echo_on
                effect_status = render_effect_status()
                sounds = regenerate_sounds()

            elif event.key == pygame.K_c:
                chorus_on = not chorus_on
                effect_status = render_effect_status()
                sounds = regenerate_sounds()

            elif event.key == pygame.K_1:
                current_waveform_idx = 0
                effect_status = render_effect_status()
                sounds = regenerate_sounds()

            elif event.key == pygame.K_2:
                current_waveform_idx = 1
                effect_status = render_effect_status()
                sounds = regenerate_sounds()

            elif event.key == pygame.K_3:
                current_waveform_idx = 2
                effect_status = render_effect_status()
                sounds = regenerate_sounds()

            elif event.key in note_map and event.key not in playing_channels:
                channel = sounds[event.key].play(-1)
                playing_channels[event.key] = channel

        elif event.type == pygame.KEYUP:
            if event.key in playing_channels:
                playing_channels[event.key].stop()
                del playing_channels[event.key]

pygame.quit()

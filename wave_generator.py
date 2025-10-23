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

WIDTH, HEIGHT = 600, 300
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Sustain Synth - Hold keys to play")

# Calculate frequency for semitone offset relative to A4 = 440 Hz
def semitone_freq(base_freq=440.0, semitone_offset=0):
    return base_freq * 2 ** (semitone_offset / 12)

# Map keys to semitone offsets (chromatic scale from A4)
# Upper row + home row, mapped logically like a piano keyboard:
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
phaser_on = False  # Phaser effect toggle

def generate_waveform(wave_type, freq, duration=DURATION, sample_rate=SAMPLE_RATE, volume=VOLUME):
    # Calculate number of full periods that fit into duration
    periods = int(freq * duration)
    duration = periods / freq  # adjust duration to fit whole periods exactly
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

    if wave_type == 'sine':
        wave = np.sin(2 * np.pi * freq * t)
    elif wave_type == 'square':
        wave = signal.square(2 * np.pi * freq * t)
    elif wave_type == 'triangle':
        wave = signal.sawtooth(2 * np.pi * freq * t, 0.5)
    else:
        raise ValueError("Invalid wave_type.")

    if wave_type == 'square':
        wave *= 0.4  # quieter square wave

    if phaser_on:
        wave = apply_phaser(wave, sample_rate=sample_rate)

    wave = volume * wave

    audio = np.int16(wave * 32767)
    return audio

def apply_phaser(wave, sample_rate=44100, depth=0.001, rate=0.5):
    max_delay_samples = depth * sample_rate
    n = len(wave)
    t = np.arange(n)
    lfo = (1 + np.sin(2 * np.pi * rate * t / sample_rate)) / 2
    delay_samples = lfo * max_delay_samples
    delayed_indices = t - delay_samples
    delayed_indices = np.clip(delayed_indices, 0, n - 1)
    delayed_wave = np.interp(delayed_indices, t, wave)
    output = 0.7 * wave + 0.3 * delayed_wave

    # Apply fade in and fade out to smooth loop edges
    fade_duration_seconds = 0.01  # 10 ms fade
    fade_samples = int(sample_rate * fade_duration_seconds)
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)

    # Apply fade-in at start
    output[:fade_samples] *= fade_in
    # Apply fade-out at end
    output[-fade_samples:] *= fade_out

    return output.astype(np.float32)

def regenerate_sounds():
    """Generate pygame Sounds for all notes with current waveform & phaser toggle."""
    new_sounds = {}
    base_freq = 440.0  # Reference frequency (A4)
    for key, semitone_offset in note_map.items():
        freq = semitone_freq(base_freq, semitone_offset)
        audio = generate_waveform(waveforms[current_waveform_idx], freq)
        new_sounds[key] = pygame.sndarray.make_sound(audio)
    return new_sounds

# Initial sounds dictionary
sounds = regenerate_sounds()
playing_channels = {}

font = pygame.font.SysFont(None, 24)
instructions1 = font.render("Hold keys A,W,S,E,D,F,T,G,Y,H,U,J,K,O,L,P to play notes.", True, (255, 255, 255))
instructions2 = font.render("Press 1: Sine  2: Square  3: Triangle", True, (255, 255, 255))
instructions3 = font.render("Press P to toggle Phaser effect ON/OFF", True, (255, 255, 255))
waveform_display = font.render(f"Current waveform: {waveforms[current_waveform_idx]}", True, (255, 255, 0))
phaser_display = font.render(f"Phaser: OFF", True, (255, 0, 0))

running = True
while running:
    screen.fill((30, 30, 30))
    screen.blit(instructions1, (10, 50))
    screen.blit(instructions2, (10, 80))
    screen.blit(instructions3, (10, 110))
    screen.blit(waveform_display, (10, 150))
    screen.blit(phaser_display, (10, 180))
    pygame.display.flip()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            # Toggle Phaser
            if event.key == pygame.K_p:
                phaser_on = not phaser_on
                phaser_display = font.render(f"Phaser: {'ON' if phaser_on else 'OFF'}", True, (0, 255, 0) if phaser_on else (255, 0, 0))
                sounds = regenerate_sounds()

            # Change waveform keys
            elif event.key == pygame.K_1:
                current_waveform_idx = 0
                waveform_display = font.render(f"Current waveform: {waveforms[current_waveform_idx]}", True, (255, 255, 0))
                sounds = regenerate_sounds()
            elif event.key == pygame.K_2:
                current_waveform_idx = 1
                waveform_display = font.render(f"Current waveform: {waveforms[current_waveform_idx]}", True, (255, 255, 0))
                sounds = regenerate_sounds()
            elif event.key == pygame.K_3:
                current_waveform_idx = 2
                waveform_display = font.render(f"Current waveform: {waveforms[current_waveform_idx]}", True, (255, 255, 0))
                sounds = regenerate_sounds()

            # Play note (only if not already playing)
            elif event.key in note_map and event.key not in playing_channels:
                channel = sounds[event.key].play(-1)  # Loop indefinitely
                playing_channels[event.key] = channel

        elif event.type == pygame.KEYUP:
            if event.key in playing_channels:
                playing_channels[event.key].stop()
                del playing_channels[event.key]

pygame.quit()

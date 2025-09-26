import os
import asyncio
import logging
import numpy as np
from dotenv import load_dotenv
from scipy.signal import resample

load_dotenv()

def get_env(key, default=None):
    return os.getenv(key, default)

def setup_log(name):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(name)

def resample_48k_to_8k(audio, orig_sr=48000, target_sr=8000):
    if orig_sr == target_sr:
        return audio
    num_samples = int(len(audio) * target_sr / orig_sr)
    return resample(audio, num_samples)

def write_wave(path, rate, data):
    import soundfile as sf
    sf.write(path, data, rate)

def read_wave(path):
    import soundfile as sf
    data, rate = sf.read(path)
    return rate, data

def preprocess_audio(data, rate, target_rate=8000):
    if not isinstance(data, np.ndarray):
        data = np.array(data)
    if len(data.shape) > 1 and data.shape[1] > 1:
        data = np.mean(data, axis=1)
    if data.dtype != np.float32:
        if data.dtype == np.int16:
            data = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            data = data.astype(np.float32) / 2147483648.0
        else:
            data = data.astype(np.float32)
    if rate != target_rate:
        data = resample_48k_to_8k(data, rate, target_rate)
        rate = target_rate
    return data, rate

import sounddevice as sd
from silero_vad import load_silero_vad, read_audio, get_speech_timestamps
import torch
import numpy as np
import ffmpeg
import requests
import os
from gtts import gTTS
import tempfile
from groq import Groq
import numpy as np
import sys
import queue
import threading
import wave
import dotenv

dotenv.load_dotenv()

def init_vars():
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    groq = Groq(api_key=GROQ_API_KEY)
    vad = load_silero_vad()


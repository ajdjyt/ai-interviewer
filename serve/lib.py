import dotenv
import os
import requests


dotenv.load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# STT: send audio to Groq Whisper API for transcription
def groqWhisper(
    filename="./recording.wav",
    api_url="https://api.groq.com/openai/v1/audio/transcriptions",
    api_key=GROQ_API_KEY,
):
    print("Sending audio to Groq Whisper API...")

    with open(filename, "rb") as audio_file:
        headers = {"Authorization": f"Bearer {api_key}"}
        files = {
            "file": (os.path.basename(filename), audio_file, "audio/wav"),
            "model": (None, "whisper-large-v3-turbo"),
        }

        response = requests.post(api_url, headers=headers, files=files)

    if response.status_code == 200:
        print("Transcription successful!")
        return response.json().get("text", "")
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None


import torch
import numpy as np
import torch
import torchaudio
from silero_vad import load_silero_vad, get_speech_timestamps


def processAudioFromArray(
    audioArray: np.ndarray, samplingRate: int = 16000, targetRate: int = 16000
) -> torch.Tensor:
    """
    Processes an audio signal stored in an np.ndarray.

    Parameters:
    - audioArray (np.ndarray): Input audio signal as a 1D numpy array.
    - samplingRate (int): Sampling rate of the input audio.
    - targetRate (int): Desired sampling rate for the output.

    Returns:
    - torch.Tensor: Processed audio signal ready for the model.
    """
    assert isinstance(audioArray, np.ndarray), "Input must be a numpy array"
    assert len(audioArray.shape) == 1, "Audio array must be one-dimensional"

    # Normalize to [-1, 1] if not already normalized
    if audioArray.dtype != np.float32:
        audioArray = audioArray.astype(np.float32) / np.max(np.abs(audioArray))

    # Resample if needed
    if samplingRate != targetRate:
        audio_tensor = torch.from_numpy(audioArray).float()
        resampler = torchaudio.transforms.Resample(
            orig_freq=samplingRate, new_freq=targetRate
        )
        audio_tensor = resampler(audio_tensor)
    else:
        audio_tensor = torch.from_numpy(audioArray).float()

    return audio_tensor


def applyVAD(audioData: np.ndarray, samplingRate: int) -> np.ndarray:
    processedAudio = processAudioFromArray(
        audioArray=audioData, samplingRate=samplingRate
    )
    speech_timestamps = get_speech_timestamps(
        audio=processedAudio, model=load_silero_vad(), samplingRate=samplingRate
    )
    return speech_timestamps

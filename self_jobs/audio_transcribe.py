from llama_hub.file.audio import AudioTranscriber
from pathlib import Path

def audio_Transcriptions(filename):
    loader = AudioTranscriber()
    result = loader.load_data(file=Path(filename))
    return result
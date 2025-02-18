import pdfplumber
import pytesseract
import cv2
import whisper
import ffmpeg
import numpy as np
from transformers import pipeline
from io import BytesIO
from app.utils.text_cleaner import clean_text, extract_entities

# Load models
whisper_model = whisper.load_model("medium")
ner_pipeline = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english")

# Process PDF
def process_pdf(file_bytes):
    text_data = []
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_data.append(text)
    return extract_entities(clean_text(" ".join(text_data)))

# Process Images
def process_image(file_bytes):
    image = cv2.imdecode(np.frombuffer(file_bytes, np.uint8), cv2.IMREAD_COLOR)
    text = pytesseract.image_to_string(image)
    return extract_entities(clean_text(text))

# Process Audio
def process_audio(file_path):
    result = whisper_model.transcribe(file_path)
    return extract_entities(clean_text(result["text"]))

# Extract audio from video
def extract_audio_from_video(video_path, output_audio_path="temp_audio.wav"):
    ffmpeg.input(video_path).output(output_audio_path).run(overwrite_output=True)
    return process_audio(output_audio_path)

# File type detection
def process_file(file_bytes, file_type):
    if "pdf" in file_type:
        return process_pdf(file_bytes)
    elif "image" in file_type:
        return process_image(file_bytes)
    elif "audio" in file_type:
        temp_file = "temp_audio.wav"
        with open(temp_file, "wb") as f:
            f.write(file_bytes)
        result = process_audio(temp_file)
        return result
    elif "video" in file_type:
        temp_file = "temp_video.mp4"
        with open(temp_file, "wb") as f:
            f.write(file_bytes)
        return extract_audio_from_video(temp_file)
    return None

# Process text messages
def process_text(text):
    return extract_entities(clean_text(text))

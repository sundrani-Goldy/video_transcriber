from fastapi import FastAPI, UploadFile, File, Depends
from sqlalchemy.orm import Session
import uvicorn
import cv2
from transformers import BlipProcessor, BlipForConditionalGeneration, pipeline
import torch
import moviepy.editor as mp
import os
import uuid
from database import SessionLocal, init_db
from models import VideoData

app = FastAPI()

# Initialize the database
init_db()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Load the BLIP image captioning model
caption_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-large")
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large")

# Load the Whisper transcription model
transcriber = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3")

# Function to generate captions
def generate_caption(image):
    inputs = processor(images=image, return_tensors="pt")
    pixel_values = inputs.pixel_values
    output_ids = caption_model.generate(pixel_values, max_length=50, num_beams=4, return_dict_in_generate=True).sequences
    caption = processor.decode(output_ids[0], skip_special_tokens=True)
    return caption

@app.post("/process-video/")
async def process_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Generate a unique ID for the video and audio files
    unique_id = str(uuid.uuid4())

    # Ensure the media directories exist
    os.makedirs('media/videos', exist_ok=True)
    os.makedirs('media/audio', exist_ok=True)

    # Save the uploaded file to the media/videos directory with a unique name
    video_filename = f"{unique_id}.mov"
    video_filepath = os.path.join('media/videos', video_filename)
    with open(video_filepath, 'wb') as f:
        f.write(await file.read())

    cap = cv2.VideoCapture(video_filepath)

    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frame_count = 0
    caption = ""
    captions = []

    # Extract audio from video with a unique name
    audio_filename = f"{unique_id}.wav"
    audio_filepath = os.path.join('media/audio', audio_filename)
    video = mp.VideoFileClip(video_filepath)
    video.audio.write_audiofile(audio_filepath)

    # Transcribe the audio
    audio_transcription = transcriber(audio_filepath)["text"]

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Generate and display the caption every 30 frames
        if frame_count % 30 == 0:
            # Generate caption
            caption = generate_caption(frame)
            timestamp = frame_count / fps  # Calculate timestamp in seconds
            print(f"Frame {frame_count}: {caption}")
            # Save the caption and timestamp
            captions.append(f"Timestamp {timestamp:.2f}s: {caption}")

        frame_count += 1

    # Release resources
    cap.release()

    # Save to database
    video_data = VideoData(
        video_path=video_filepath,
        audio_path=audio_filepath,  # Include audio_path
        transcription=audio_transcription,
        captions="\n".join(captions)
    )
    db.add(video_data)
    db.commit()
    db.refresh(video_data)

    return {
        "video_data_id": video_data.id,
        "video_path": video_filepath,
        "audio_path": audio_filepath,
        "captions": captions,
        "transcription": audio_transcription
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

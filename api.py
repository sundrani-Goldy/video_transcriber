from fastapi import FastAPI, UploadFile, File, Depends
from sqlalchemy.orm import Session
import uvicorn
import cv2
from transformers import BlipProcessor, BlipForConditionalGeneration, pipeline
import torch
import moviepy.editor as mp
import tempfile
import os
from database import SessionLocal, init_db, engine
from models import VideoData
from sqlalchemy.orm import sessionmaker

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
    # Save the uploaded file to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mov") as tmp:
        tmp.write(await file.read())
        video_path = tmp.name

    cap = cv2.VideoCapture(video_path)

    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec

    # Define the output video
    output_path = 'video_with_captions.mp4'
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_count = 0
    caption = ""
    captions = []

    # Extract audio from video
    audio_path = 'audio.wav'
    video = mp.VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path)

    # Transcribe the audio
    audio_transcription = transcriber(audio_path)["text"]

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

        # Display caption on the frame
        cv2.putText(frame, caption, (10, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

        # Write the frame to the output video
        out.write(frame)

        frame_count += 1

    # Release resources
    cap.release()
    out.release()

    # Save to database
    video_data = VideoData(
        video_path=output_path,
        transcription=audio_transcription,
        captions="\n".join(captions)
    )
    db.add(video_data)
    db.commit()
    db.refresh(video_data)

    return {"video_data_id": video_data.id, "output_video": output_path, "captions": captions, "transcription": audio_transcription}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

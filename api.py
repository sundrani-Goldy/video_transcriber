import os
from fastapi import FastAPI, UploadFile, File, Depends, BackgroundTasks
from sqlalchemy.orm import Session
import uuid
from database import SessionLocal, init_db
from models import VideoData
from utils import transcribe_and_generate_captions, validate_video
import asyncio
from transformers import BlipProcessor, BlipForConditionalGeneration, pipeline

app = FastAPI()

# Initialize the database
init_db()

# Ensure the media directories exist
os.makedirs('media/videos', exist_ok=True)
os.makedirs('media/audio', exist_ok=True)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Asynchronous function to download models
async def download_models():
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large")
    caption_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-large")
    transcriber = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3")

# Startup event to download models
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(download_models())

@app.post("/process-video/")
async def process_video(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Generate a unique ID for the video and audio files
    unique_id = str(uuid.uuid4())

    # Save the uploaded file to the media/videos directory with a unique name
    video_filename = f"{unique_id}.mov"
    video_filepath = os.path.join('media/videos', video_filename)
    with open(video_filepath, 'wb') as f:
        f.write(await file.read())

    # Validate the uploaded video file
    valid, error_message, duration, fps, width, height = validate_video(video_filepath)
    if not valid:
        return {"message": f"Error processing video: {error_message}"}

    # Define paths for audio file and output video
    audio_filename = f"{unique_id}.wav"
    audio_filepath = os.path.join('media/audio', audio_filename)

    # Add the Celery task to the background tasks
    background_tasks.add_task(transcribe_and_generate_captions, video_filepath, audio_filepath, db, unique_id)

    return {"message": "Video is being processed", "video_id": unique_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

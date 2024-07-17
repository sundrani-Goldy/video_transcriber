import os
from fastapi import FastAPI, UploadFile, File, Depends, BackgroundTasks
from sqlalchemy.orm import Session
import uuid
from database import SessionLocal, init_db
from models import VideoData
from utils import transcribe_and_generate_captions, validate_video

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

@app.post("/process-videos/")
async def process_videos(background_tasks: BackgroundTasks, files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    responses = []
    for file in files:
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
            responses.append({"message": f"Error processing video: {error_message}", "video_id": unique_id})
            continue

        # Define paths for audio file
        audio_filename = f"{unique_id}.wav"
        audio_filepath = os.path.join('media/audio', audio_filename)

        # Add the Celery task to the background tasks
        background_tasks.add_task(transcribe_and_generate_captions, video_filepath, audio_filepath, db, unique_id)

        responses.append({"message": "Video is being processed", "video_id": unique_id})

    return responses

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

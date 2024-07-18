import os
from fastapi import FastAPI, UploadFile, File, Depends
from sqlalchemy.orm import Session
from celery.result import AsyncResult
import uuid
from database import SessionLocal, init_db
from models import VideoData
from utils import validate_video
from celery_worker import transcribe_and_generate_captions
import asyncio
from transformers import BlipProcessor, BlipForConditionalGeneration, pipeline
from fastapi.middleware.cors import CORSMiddleware

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

# Add CORS middleware
origins = [
    "http://localhost:3000",
    # Add other origins if necessary
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
async def process_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
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
    task = transcribe_and_generate_captions.apply_async(args=[video_filepath, audio_filepath, unique_id])

    return {"message": "Video is being processed", "video_id": unique_id, "task_id": task.id}

@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    task_result = AsyncResult(task_id)
    if task_result.state == 'PENDING':
        response = {
            'state': task_result.state,
            'status': 'Pending...',
        }
    elif task_result.state != 'FAILURE':
        response = {
            'state': task_result.state,
            'status': task_result.info.get('status', ''),
            'progress': task_result.info.get('current', 0) / task_result.info.get('total', 1) * 100
        }
        if 'result' in task_result.info:
            response['result'] = task_result.info['result']
    else:
        response = {
            'state': task_result.state,
            'status': str(task_result.info),  # this is the exception raised
        }
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

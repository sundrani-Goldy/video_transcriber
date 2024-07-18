from celery import Celery
from celery.utils.log import get_task_logger
from celery import current_task
from database import SessionLocal, init_db  # Import your database setup

celery_app = Celery(
    "video_processor",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

# Initialize the database
init_db()

@celery_app.task(bind=True)
def transcribe_and_generate_captions(self, video_filepath, audio_filepath, unique_id):
    from utils import validate_video, generate_caption, transcriber
    from models import VideoData
    import cv2
    import moviepy.editor as mp

    db = SessionLocal()

    valid, error_message, duration, fps, width, height = validate_video(video_filepath)
    if not valid:
        raise ValueError(f"Error validating video: {error_message}")

    cap = cv2.VideoCapture(video_filepath)

    frame_count = 0
    caption = ""
    captions = []

    # Extract audio from video with a unique name
    video = mp.VideoFileClip(video_filepath)
    video.audio.write_audiofile(audio_filepath)

    # Transcribe the audio
    audio_transcription = transcriber(audio_filepath)["text"]

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

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
        self.update_state(state='PROGRESS', meta={'current': frame_count, 'total': total_frames})

    # Release resources
    cap.release()

    # Save to database
    video_data = VideoData(
        video_path=video_filepath,
        audio_path=audio_filepath,
        transcription=audio_transcription,
        captions="\n".join(captions)
    )
    db.add(video_data)
    db.commit()
    db.refresh(video_data)

    return {'current': total_frames, 'total': total_frames, 'status': 'Task completed!', 'result': video_data.id}

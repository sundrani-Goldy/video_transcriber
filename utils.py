# utils.py

from celery import current_task
import cv2
from transformers import BlipProcessor, BlipForConditionalGeneration, pipeline
import moviepy.editor as mp
from moviepy.editor import VideoFileClip
from models import VideoData

# Load the BLIP image captioning model
caption_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-large")
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large")

# Load the Whisper transcription model
transcriber = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3")

def generate_caption(image):
    inputs = processor(images=image, return_tensors="pt")
    pixel_values = inputs.pixel_values
    output_ids = caption_model.generate(pixel_values, max_length=50, num_beams=4, return_dict_in_generate=True).sequences
    caption = processor.decode(output_ids[0], skip_special_tokens=True)
    return caption

def validate_video(file_path):
    try:
        clip = VideoFileClip(file_path)
        duration = clip.duration
        fps = clip.fps
        width = clip.size[0]
        height = clip.size[1]
        return True, None, duration, fps, width, height  # Return None for error_message if successful
    except Exception as e:
        return False, str(e), None, None, None, None  # Return None for duration, fps, width, height if validation fails

def transcribe_and_generate_captions(video_filepath, audio_filepath, db, unique_id):
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

        # Report progress to Celery
        current_task.update_state(state='PROGRESS', meta={'current': frame_count, 'total': total_frames})

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

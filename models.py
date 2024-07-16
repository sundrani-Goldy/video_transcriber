from sqlalchemy import Column, Integer, String, Text
from database import Base

class VideoData(Base):
    __tablename__ = "video_data"

    id = Column(Integer, primary_key=True, index=True)
    video_path = Column(String, index=True)
    audio_path = Column(String, index=True)  # Add this line
    transcription = Column(Text)
    captions = Column(Text)

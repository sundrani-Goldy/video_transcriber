# interface.py

import requests

def process_video(video):
    files = {'file': video}
    response = requests.post("http://0.0.0.0:8000/process-video/", files=files)
    return response.json()

# No need for Gradio interface

# Use the official Python image from the Docker Hub
FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY req.txt .

# Install dependencies
RUN pip install --no-cache-dir -r req.txt

# Download the models during the build process
RUN python -c "from transformers import BlipProcessor, BlipForConditionalGeneration; BlipProcessor.from_pretrained('Salesforce/blip-image-captioning-large'); BlipForConditionalGeneration.from_pretrained('Salesforce/blip-image-captioning-large')"
RUN python -c "from transformers import pipeline; pipeline('automatic-speech-recognition', model='openai/whisper-large-v3')"

# Copy the rest of the application code into the container
COPY . .

# Expose the port that the FastAPI app runs on
EXPOSE 8000

# Run the command to start the FastAPI application
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]

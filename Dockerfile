# Use the official Python 3.11 image from the Docker Hub
FROM python:3.11

# Set the working directory in the container to /app
WORKDIR /app

# Set environment variables to prevent Python from buffering its output
ENV PYTHONUNBUFFERED=1

# Install system dependencies and update pip
RUN apt-get update && apt-get install -y \
    libpq-dev \
    && pip install --upgrade pip

# Copy the requirements file into the container at /app
COPY ./requirements.txt /app/

# Install the Python dependencies from requirements.txt
RUN pip install -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . /app/

# Expose port 8000 for the Flask app to listen on
EXPOSE 8000

# Define the command to run the Flask app
CMD ["fastapi","dev", "api.py", "--host", "0.0.0.0", "--port", "8000"]
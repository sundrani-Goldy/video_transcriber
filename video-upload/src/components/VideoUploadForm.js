// src/components/VideoUploadForm.js
"use client"; // Add this line

import React, { useState, useEffect } from 'react';
import axios from 'axios';

const VideoUploadForm = () => {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processingMessage, setProcessingMessage] = useState('');
  const [taskId, setTaskId] = useState('');
  const [taskStatus, setTaskStatus] = useState('');
  const [progress, setProgress] = useState(0);

  const handleFileChange = (e) => {
    setSelectedFiles(e.target.files);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData();
    for (let i = 0; i < selectedFiles.length; i++) {
      formData.append('file', selectedFiles[i]);
    }

    try {
      const response = await axios.post('http://127.0.0.1:8000/process-video/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Accept': 'application/json',
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted);
        },
      });
      setProcessingMessage(response.data.message);
      setTaskId(response.data.task_id);  // Save the task ID to check the status later
      setUploadProgress(0); // Reset progress after upload
      setSelectedFiles([]);
    } catch (error) {
      console.error('Error uploading files:', error);
    }
  };

  useEffect(() => {
    if (taskId) {
      const interval = setInterval(async () => {
        try {
          const response = await axios.get(`http://127.0.0.1:8000/task-status/${taskId}`);
          setTaskStatus(response.data.state);
          setProgress(response.data.progress);

          if (response.data.state === 'SUCCESS' || response.data.state === 'FAILURE') {
            clearInterval(interval);
          }
        } catch (error) {
          console.error('Error fetching task status:', error);
        }
      }, 1000);

      return () => clearInterval(interval);
    }
  }, [taskId]);

  return (
    <div>
      <h2>Upload Video</h2>
      <form onSubmit={handleSubmit}>
        <input type="file" multiple onChange={handleFileChange} />
        <button type="submit">Upload</button>
      </form>
      {uploadProgress > 0 && (
        <div>
          <h3>Upload Progress</h3>
          <progress value={uploadProgress} max="100" />
          <span>{uploadProgress}%</span>
        </div>
      )}
      {processingMessage && (
        <div>
          <h3>{processingMessage}</h3>
          {taskStatus && <p>Task Status: {taskStatus}</p>}
          {progress > 0 && (
            <div>
              <h3>Processing Progress</h3>
              <progress value={progress} max="100" />
              <span>{progress}%</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default VideoUploadForm;

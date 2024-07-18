// src/app/page.js
import Head from 'next/head';
import VideoUploadForm from '../components/VideoUploadForm';

export default function Home() {
  return (
    <div>
      <Head>
        <title>Video Upload</title>
      </Head>
      <main>
        <h1>Upload Your Videos</h1>
        <VideoUploadForm />
      </main>
    </div>
  );
}

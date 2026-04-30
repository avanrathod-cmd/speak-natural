/** Drag-and-drop audio upload screen shown before a call is analyzed. */

import React, { useRef, useState } from 'react';
import { Upload } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function UploadView({
  onFile,
  quotaReached = false,
}: {
  onFile: (file: File) => void;
  quotaReached?: boolean;
}) {
  const navigate = useNavigate();
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  if (quotaReached) {
    return (
      <div className="border-2 border-dashed border-gray-200 rounded-2xl
        p-16 text-center bg-gray-50"
      >
        <div className="w-16 h-16 bg-red-100 rounded-full flex
          items-center justify-center mx-auto mb-4"
        >
          <Upload className="w-8 h-8 text-red-400" />
        </div>
        <h2 className="text-xl font-semibold text-gray-700 mb-2">
          Analysis quota reached
        </h2>
        <p className="text-gray-500 mb-4">
          You've used all 4 hours of free analysis.
        </p>
        <button
          onClick={() => navigate('/pricing')}
          className="text-sm font-medium bg-blue-600 text-white
            rounded-lg px-5 py-2 hover:bg-blue-700"
        >
          Upgrade to continue →
        </button>
      </div>
    );
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) onFile(file);
  }

  return (
    <div
      className={`border-2 border-dashed rounded-2xl p-16 text-center cursor-pointer transition-colors ${
        dragging
          ? 'border-blue-400 bg-blue-50'
          : 'border-gray-300 bg-white hover:border-blue-300 hover:bg-gray-50'
      }`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => fileRef.current?.click()}
    >
      <input
        ref={fileRef}
        type="file"
        accept="audio/*"
        className="hidden"
        onChange={(e) => {
          if (e.target.files?.[0]) onFile(e.target.files[0]);
        }}
      />
      <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <Upload className="w-8 h-8 text-blue-600" />
      </div>
      <h2 className="text-xl font-semibold text-gray-800 mb-2">
        Upload a sales call
      </h2>
      <p className="text-gray-500 mb-1">Drag and drop or click to select</p>
      <p className="text-sm text-gray-400">MP3, WAV, M4A — up to 500 MB</p>
    </div>
  );
}

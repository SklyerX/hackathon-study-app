'use client'

import { Button } from '@/components/ui/button';
import { FileUpload, FileUploadDropzone, FileUploadItem, FileUploadItemDelete, FileUploadItemMetadata, FileUploadItemPreview, FileUploadList, FileUploadTrigger } from '@/components/ui/file-upload'
import { Sparkle, Upload, X } from 'lucide-react';
import { redirect } from 'next/navigation';
import React, { useState } from 'react'
import { toast } from 'sonner';

export default function Page() {
  const [files, setFiles] = useState<File[]>([]);

  const onFileReject = React.useCallback((file: File, message: string) => {
    toast(message, {
      description: `"${file.name.length > 20 ? `${file.name.slice(0, 20)}...` : file.name}" has been rejected`,
    });
  }, []);

  const handleUpload = async () => {
    const form = new FormData();

    for (const file of files) {
      form.append("file", file)
    }

    const res = await fetch("http://localhost:9999/api/ingestion/upload", {
      method: "POST",
      body: form
    });

    if (!res.ok) return toast.error("Upload failed", { description: "Failed to upload files!" })

    const data = await res.json();

    if (!data.session_id) return toast.error("No session id was returned");

    redirect(`/${data.session_id}`)
  }

  return (
    <div>
      <h3 className="text-4xl font-semibold">Upload</h3>
      <p className='text-muted-foreground'>Please upload all of your content that you would like to study, such as lecture notes, lecture slides, audio files, images, etc.</p>

      <FileUpload
        maxFiles={20}
        maxSize={50 * 1024 * 1024}
        accept="audio/mpeg,audio/mp3,audio/wav,audio/x-wav,audio/ogg,audio/webm,audio/m4a,audio/mp4,image/jpeg,image/png,image/gif,image/webp,image/bmp,image/tiff,application/pdf"
        className="w-full mt-4"
        value={files}
        onValueChange={setFiles}
        onFileReject={onFileReject}
        multiple
      >
        <FileUploadDropzone>
          <div className="flex flex-col items-center gap-1 text-center">
            <div className="flex items-center justify-center rounded-full border p-2.5">
              <Upload className="size-6 text-muted-foreground" />
            </div>
            <p className="font-medium text-sm">Drag & drop files here</p>
            <p className="text-muted-foreground text-xs">
              Or click to browse (max 20 files, up to 50MB each)
            </p>
          </div>
          <FileUploadTrigger asChild>
            <Button variant="outline" size="sm" className="mt-2 w-fit">
              Browse files
            </Button>
          </FileUploadTrigger>
        </FileUploadDropzone>
        <FileUploadList>
          {files.map((file, index) => (
            <FileUploadItem key={index} value={file}>
              <FileUploadItemPreview />
              <FileUploadItemMetadata />
              <FileUploadItemDelete asChild>
                <Button variant="ghost" size="icon" className="size-7">
                  <X />
                </Button>
              </FileUploadItemDelete>
            </FileUploadItem>
          ))}
        </FileUploadList>
      </FileUpload>

      {files.length > 0 ? <Button className='mt-3 w-full' size="lg" onClick={handleUpload}>
        <Sparkle className='size-4' /> Upload!
      </Button> : null}
    </div>
  )
}
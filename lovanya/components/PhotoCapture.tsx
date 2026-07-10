"use client";

import { useEffect, useRef, useState } from "react";
import { Camera, GalleryAdd, Refresh } from "iconsax-react";

/**
 * Camera capture with a graceful upload fallback.
 * Returns a JPEG data-URL via onCapture.
 */
export default function PhotoCapture({
  onCapture,
  facing = "environment",
  hint,
}: {
  onCapture: (dataUrl: string) => void;
  facing?: "user" | "environment";
  hint?: string;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<"starting" | "camera" | "upload-only">(
    "starting"
  );
  const [mirror, setMirror] = useState(facing === "user");

  useEffect(() => {
    let cancelled = false;
    async function start() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: facing },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play().catch(() => {});
        }
        setMode("camera");
      } catch {
        if (!cancelled) setMode("upload-only");
      }
    }
    start();
    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    };
  }, [facing]);

  const snap = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    const maxDim = 900;
    const scale = Math.min(1, maxDim / Math.max(video.videoWidth, video.videoHeight));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    if (mirror) {
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1);
    }
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    onCapture(canvas.toDataURL("image/jpeg", 0.82));
  };

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
      onCapture(String(reader.result));
    };
    reader.readAsDataURL(file);
  };

  return (
    <div>
      <div className="relative aspect-[3/4] overflow-hidden rounded-[1.8rem] border border-line bg-blush">
        {mode !== "upload-only" ? (
          <video
            ref={videoRef}
            playsInline
            muted
            className="h-full w-full object-cover"
            style={mirror ? { transform: "scaleX(-1)" } : undefined}
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-3 px-8 text-center">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-card text-rosewood shadow-soft">
              <GalleryAdd size={24} />
            </span>
            <p className="text-sm text-ink-soft">
              No camera here — no problem. Choose a photo instead.
            </p>
          </div>
        )}

        {mode === "camera" && (
          <div className="absolute inset-x-0 bottom-0 flex items-center justify-center gap-8 bg-gradient-to-t from-ink/45 to-transparent px-6 pb-5 pt-12">
            <button
              onClick={() => fileRef.current?.click()}
              aria-label="Upload a photo"
              className="flex h-11 w-11 items-center justify-center rounded-full bg-white/25 text-white backdrop-blur active:scale-95"
            >
              <GalleryAdd size={19} />
            </button>
            <button
              onClick={snap}
              aria-label="Take photo"
              className="h-[68px] w-[68px] rounded-full border-4 border-white bg-white/30 backdrop-blur transition-transform active:scale-90"
            />
            <button
              onClick={() => setMirror((m) => !m)}
              aria-label="Flip preview"
              className="flex h-11 w-11 items-center justify-center rounded-full bg-white/25 text-white backdrop-blur active:scale-95"
            >
              <Refresh size={18} />
            </button>
          </div>
        )}

        {mode === "starting" && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="flex items-center gap-2 rounded-full bg-card/80 px-4 py-2 text-sm text-ink-soft backdrop-blur">
              <Camera size={15} /> opening camera…
            </span>
          </div>
        )}
      </div>

      {mode === "upload-only" && (
        <button
          onClick={() => fileRef.current?.click()}
          className="mt-4 w-full rounded-full bg-gradient-to-br from-rosewood to-rosewood-deep py-3.5 font-semibold text-white shadow-lift active:scale-[0.98]"
        >
          Choose a photo
        </button>
      )}

      {hint && (
        <p className="mt-3 text-center text-[13px] text-ink-soft">{hint}</p>
      )}

      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={onFile}
      />
    </div>
  );
}

"use client";

import {
  AlertCircle,
  ImageIcon,
  Video,
} from "lucide-react";
import { useState } from "react";

type EvidenceMediaProps = {
  imageUrl: string | null;
  clipUrl: string | null;
};

export function EvidenceMedia({
  imageUrl,
  clipUrl,
}: EvidenceMediaProps) {
  const [
    imageFailed,
    setImageFailed,
  ] = useState(false);

  const [
    clipFailed,
    setClipFailed,
  ] = useState(false);

  return (
    <div className="space-y-6">
      <section>
        <div className="mb-3 flex items-center gap-2">
          <ImageIcon
            size={18}
            className="text-cyan-700"
          />

          <h3 className="font-semibold text-slate-950">
            Evidence image
          </h3>
        </div>

        {imageUrl && !imageFailed ? (
          <div className="overflow-hidden rounded-xl bg-slate-950">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={imageUrl}
              alt="Traffic violation evidence"
              onError={() =>
                setImageFailed(true)
              }
              className="max-h-[520px] w-full object-contain"
            />
          </div>
        ) : (
          <div className="flex min-h-64 flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 px-5 text-center">
            <ImageIcon
              size={31}
              className="text-slate-300"
            />

            <p className="mt-3 text-sm font-medium text-slate-600">
              Evidence image unavailable
            </p>

            <p className="mt-1 text-xs text-slate-400">
              This violation does not have a
              captured evidence frame.
            </p>
          </div>
        )}
      </section>

      <section>
        <div className="mb-3 flex items-center gap-2">
          <Video
            size={18}
            className="text-cyan-700"
          />

          <h3 className="font-semibold text-slate-950">
            Annotated evidence clip
          </h3>
        </div>

        {clipUrl && !clipFailed ? (
          <video
            controls
            preload="metadata"
            src={clipUrl}
            onError={() =>
              setClipFailed(true)
            }
            className="aspect-video w-full rounded-xl bg-black"
          >
            Your browser does not support video
            playback.
          </video>
        ) : (
          <div className="flex min-h-64 flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 px-5 text-center">
            {clipFailed ? (
              <AlertCircle
                size={31}
                className="text-rose-400"
              />
            ) : (
              <Video
                size={31}
                className="text-slate-300"
              />
            )}

            <p className="mt-3 text-sm font-medium text-slate-600">
              Evidence clip unavailable
            </p>

            <p className="mt-1 text-xs text-slate-400">
              No annotated clip is attached to
              this violation.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}

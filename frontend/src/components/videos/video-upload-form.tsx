"use client";

import {
  AlertCircle,
  CheckCircle2,
  FileVideo,
  LoaderCircle,
  Upload,
  X,
} from "lucide-react";
import Link from "next/link";
import {
  type ChangeEvent,
  type DragEvent,
  useRef,
  useState,
} from "react";

import { uploadVideo } from "@/lib/api/resources";
import { formatFileSize } from "@/lib/utils/format";
import type {
  Camera,
  VideoUploadResponse,
} from "@/types/api";

type VideoUploadFormProps = {
  cameras: Camera[];
  camerasAvailable: boolean;
};

const supportedExtensions = [
  ".mp4",
  ".mov",
  ".mkv",
  ".avi",
  ".webm",
  ".m4v",
];

const maximumFileSizeBytes =
  500 * 1024 * 1024;

export function VideoUploadForm({
  cameras,
  camerasAvailable,
}: VideoUploadFormProps) {
  const inputRef =
    useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] =
    useState<File | null>(null);

  const [cameraId, setCameraId] =
    useState("");

  const [priority, setPriority] =
    useState(0);

  const [uploadProgress, setUploadProgress] =
    useState(0);

  const [isUploading, setIsUploading] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const [result, setResult] =
    useState<VideoUploadResponse | null>(
      null,
    );

  function validateFile(
    file: File,
  ): string | null {
    const lowercaseName =
      file.name.toLowerCase();

    const hasSupportedExtension =
      supportedExtensions.some(
        (extension) =>
          lowercaseName.endsWith(
            extension,
          ),
      );

    if (!hasSupportedExtension) {
      return `Unsupported video format. Use ${supportedExtensions.join(
        ", ",
      )}.`;
    }

    if (
      file.size > maximumFileSizeBytes
    ) {
      return "The video exceeds the 500 MB upload limit.";
    }

    if (file.size === 0) {
      return "The selected file is empty.";
    }

    return null;
  }

  function selectFile(file: File) {
    const validationError =
      validateFile(file);

    setError(validationError);
    setResult(null);

    if (validationError) {
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
    setUploadProgress(0);
  }

  function handleFileChange(
    event: ChangeEvent<HTMLInputElement>,
  ) {
    const file =
      event.target.files?.[0];

    if (file) {
      selectFile(file);
    }
  }

  function handleDrop(
    event: DragEvent<HTMLDivElement>,
  ) {
    event.preventDefault();

    const file =
      event.dataTransfer.files[0];

    if (file) {
      selectFile(file);
    }
  }

  function clearFile() {
    setSelectedFile(null);
    setUploadProgress(0);
    setError(null);
    setResult(null);

    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  async function handleUpload() {
    if (!selectedFile) {
      setError(
        "Choose a traffic video first.",
      );

      return;
    }

    setIsUploading(true);
    setError(null);
    setResult(null);
    setUploadProgress(0);

    try {
      const response = await uploadVideo({
        file: selectedFile,
        cameraId:
          cameraId || undefined,
        priority,
        onProgress: setUploadProgress,
      });

      setResult(response);
      setUploadProgress(100);
    } catch (uploadError) {
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : "The video could not be uploaded.",
      );
    } finally {
      setIsUploading(false);
    }
  }

  if (result) {
    return (
      <section className="rounded-2xl border border-emerald-200 bg-white p-8 shadow-sm">
        <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700">
          <CheckCircle2 size={28} />
        </span>

        <h3 className="mt-5 text-xl font-bold text-slate-950">
          Video accepted for processing
        </h3>

        <p className="mt-2 text-sm leading-6 text-slate-500">
          The video was stored successfully
          and a processing job was created.
        </p>

        <dl className="mt-6 grid gap-4 rounded-2xl bg-slate-50 p-5 sm:grid-cols-2">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Filename
            </dt>

            <dd className="mt-1 break-all text-sm font-medium text-slate-900">
              {result.video.original_filename}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Video status
            </dt>

            <dd className="mt-1 text-sm font-medium capitalize text-slate-900">
              {result.video.status}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Processing job
            </dt>

            <dd className="mt-1 break-all text-sm font-medium text-slate-900">
              {result.processing_job.id}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Job status
            </dt>

            <dd className="mt-1 text-sm font-medium capitalize text-slate-900">
              {result.processing_job.status}
            </dd>
          </div>
        </dl>

        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <Link
            href="/jobs"
            className="inline-flex h-11 items-center justify-center rounded-xl bg-slate-950 px-5 text-sm font-semibold text-white"
          >
            View processing jobs
          </Link>

          <button
            type="button"
            onClick={clearFile}
            className="inline-flex h-11 items-center justify-center rounded-xl border border-slate-200 px-5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            Upload another video
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="grid gap-6 xl:grid-cols-[1.4fr_0.8fr]">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div
          onDragOver={(event) =>
            event.preventDefault()
          }
          onDrop={handleDrop}
          onClick={() =>
            !isUploading &&
            inputRef.current?.click()
          }
          className={[
            "flex min-h-72 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 text-center transition-colors",
            selectedFile
              ? "border-cyan-400 bg-cyan-50/40"
              : "border-slate-300 bg-slate-50 hover:border-cyan-500 hover:bg-cyan-50/40",
            isUploading
              ? "pointer-events-none opacity-70"
              : "",
          ].join(" ")}
        >
          <input
            ref={inputRef}
            type="file"
            accept={supportedExtensions.join(
              ",",
            )}
            onChange={handleFileChange}
            className="sr-only"
          />

          {selectedFile ? (
            <>
              <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-cyan-500 text-slate-950">
                <FileVideo size={26} />
              </span>

              <p className="mt-5 max-w-lg break-all text-base font-semibold text-slate-950">
                {selectedFile.name}
              </p>

              <p className="mt-2 text-sm text-slate-500">
                {formatFileSize(
                  selectedFile.size,
                )}
              </p>

              {!isUploading ? (
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    clearFile();
                  }}
                  className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-rose-600"
                >
                  <X size={16} />
                  Remove file
                </button>
              ) : null}
            </>
          ) : (
            <>
              <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-cyan-500 text-slate-950">
                <Upload size={25} />
              </span>

              <span className="mt-5 text-base font-semibold text-slate-950">
                Choose a traffic video
              </span>

              <span className="mt-2 max-w-md text-sm leading-6 text-slate-500">
                Drag and drop a video here
                or click to browse your
                computer.
              </span>

              <span className="mt-3 text-xs text-slate-400">
                MP4, MOV, MKV, AVI, WEBM or
                M4V · Maximum 500 MB
              </span>
            </>
          )}
        </div>

        {isUploading ? (
          <div className="mt-5">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-slate-700">
                Uploading video
              </span>

              <span className="text-slate-500">
                {uploadProgress}%
              </span>
            </div>

            <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-cyan-500 transition-[width]"
                style={{
                  width: `${uploadProgress}%`,
                }}
              />
            </div>
          </div>
        ) : null}

        {error ? (
          <div className="mt-5 flex gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            <AlertCircle
              size={19}
              className="mt-0.5 shrink-0"
            />

            <p>{error}</p>
          </div>
        ) : null}

        <button
          type="button"
          disabled={
            !selectedFile ||
            isUploading
          }
          onClick={() => {
            void handleUpload();
          }}
          className="mt-5 inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {isUploading ? (
            <>
              <LoaderCircle
                size={18}
                className="animate-spin"
              />
              Uploading…
            </>
          ) : (
            <>
              <Upload size={18} />
              Start analysis
            </>
          )}
        </button>
      </div>

      <aside className="space-y-6">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="font-semibold text-slate-950">
            Analysis settings
          </h3>

          <label className="mt-5 block">
            <span className="text-sm font-medium text-slate-700">
              Camera
            </span>

            <select
              value={cameraId}
              onChange={(event) =>
                setCameraId(
                  event.target.value,
                )
              }
              disabled={
                !camerasAvailable ||
                isUploading
              }
              className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none focus:border-cyan-500 disabled:bg-slate-100"
            >
              <option value="">
                No camera assigned
              </option>

              {cameras.map((camera) => (
                <option
                  key={camera.id}
                  value={camera.id}
                >
                  {camera.name}
                </option>
              ))}
            </select>

            {!camerasAvailable ? (
              <span className="mt-2 block text-xs text-amber-700">
                Camera records could not be
                loaded.
              </span>
            ) : null}
          </label>

          <label className="mt-5 block">
            <span className="flex items-center justify-between text-sm font-medium text-slate-700">
              <span>Processing priority</span>
              <span>{priority}</span>
            </span>

            <input
              type="range"
              min="-10"
              max="10"
              step="1"
              value={priority}
              disabled={isUploading}
              onChange={(event) =>
                setPriority(
                  Number(
                    event.target.value,
                  ),
                )
              }
              className="mt-3 w-full accent-cyan-500"
            />

            <span className="mt-2 flex justify-between text-xs text-slate-400">
              <span>Low</span>
              <span>Normal</span>
              <span>High</span>
            </span>
          </label>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="font-semibold text-slate-950">
            Analysis capabilities
          </h3>

          <ul className="mt-4 space-y-3 text-sm text-slate-600">
            <li>• Vehicle and rider tracking</li>
            <li>• Triple-riding detection</li>
            <li>• Helmet violation detection</li>
            <li>• Wrong-way driving detection</li>
            <li>• Lane-violation detection</li>
            <li>• Red-light violation detection</li>
          </ul>
        </div>
      </aside>
    </section>
  );
}

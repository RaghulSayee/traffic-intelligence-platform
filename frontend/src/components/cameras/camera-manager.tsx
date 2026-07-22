"use client";

import {
  ConfirmDialog,
} from "@/components/ui/confirm-dialog";

import {
  AlertCircle,
  Camera as CameraIcon,
  CheckCircle2,
  LoaderCircle,
  MapPin,
  Pencil,
  Plus,
  Power,
  Save,
  Search,
  Settings2,
  Trash2,
  Wifi,
  X,
} from "lucide-react";
import Link from "next/link";
import {
  useMemo,
  useState,
} from "react";
import {
  MobileTableNotice,
} from "@/components/ui/mobile-table-notice";

import type {
  FormEvent,
} from "react";

import {
  createCamera,
  deleteCamera,
  updateCamera,
} from "@/lib/api/cameras";
import type {
  Camera,
  CameraCreatePayload,
  CameraListResponse,
  CameraStatus,
} from "@/types/cameras";

type CameraManagerProps = {
  initialResponse: CameraListResponse;
};

type CameraFormModalProps = {
  camera: Camera | null;
  onClose: () => void;
  onSaved: (camera: Camera) => void;
};

type CameraFormState = {
  name: string;
  location: string;
  description: string;
  streamUrl: string;
  status: CameraStatus;
  latitude: string;
  longitude: string;
  configuredFps: string;
  resolutionWidth: string;
  resolutionHeight: string;
};

const cameraStatuses: Array<{
  value: CameraStatus;
  label: string;
}> = [
  {
    value: "inactive",
    label: "Inactive",
  },
  {
    value: "active",
    label: "Active",
  },
  {
    value: "degraded",
    label: "Degraded",
  },
  {
    value: "offline",
    label: "Offline",
  },
];

const statusStyles: Record<
  CameraStatus,
  string
> = {
  active:
    "bg-emerald-50 text-emerald-700",
  inactive:
    "bg-slate-100 text-slate-600",
  degraded:
    "bg-amber-50 text-amber-700",
  offline:
    "bg-rose-50 text-rose-700",
};

function initialFormState(
  camera: Camera | null,
): CameraFormState {
  return {
    name: camera?.name ?? "",
    location: camera?.location ?? "",
    description:
      camera?.description ?? "",
    streamUrl:
      camera?.stream_url ?? "",
    status:
      camera?.status ?? "inactive",
    latitude:
      camera?.latitude?.toString() ??
      "",
    longitude:
      camera?.longitude?.toString() ??
      "",
    configuredFps:
      camera?.configured_fps?.toString() ??
      "",
    resolutionWidth:
      camera?.resolution_width?.toString() ??
      "",
    resolutionHeight:
      camera?.resolution_height?.toString() ??
      "",
  };
}

function optionalText(
  value: string,
): string | null {
  const normalized =
    value.trim();

  return normalized || null;
}

function optionalNumber(
  value: string,
): number | null {
  if (!value.trim()) {
    return null;
  }

  const parsed =
    Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : null;
}

function formatDate(
  value: string,
): string {
  const date = new Date(value);

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return "Not available";
  }

  return new Intl.DateTimeFormat(
    "en-US",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  ).format(date);
}

function CameraFormModal({
  camera,
  onClose,
  onSaved,
}: CameraFormModalProps) {
  const [
    form,
    setForm,
  ] = useState(
    initialFormState(camera),
  );

  const [
    submitting,
    setSubmitting,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState<string | null>(
    null,
  );

  const isEditing =
    camera !== null;

  function updateField<
    Key extends keyof CameraFormState,
  >(
    key: Key,
    value: CameraFormState[Key],
  ) {
    setForm((current) => ({
      ...current,
      [key]: value,
    }));

    setError(null);
  }

  function validate(): string | null {
    if (form.name.trim().length < 2) {
      return "Camera name must contain at least two characters.";
    }

    const latitude =
      optionalNumber(form.latitude);

    const longitude =
      optionalNumber(form.longitude);

    const fps =
      optionalNumber(
        form.configuredFps,
      );

    const width =
      optionalNumber(
        form.resolutionWidth,
      );

    const height =
      optionalNumber(
        form.resolutionHeight,
      );

    if (
      latitude !== null &&
      (
        latitude < -90 ||
        latitude > 90
      )
    ) {
      return "Latitude must be between -90 and 90.";
    }

    if (
      longitude !== null &&
      (
        longitude < -180 ||
        longitude > 180
      )
    ) {
      return "Longitude must be between -180 and 180.";
    }

    if (
      fps !== null &&
      (
        fps <= 0 ||
        fps > 240
      )
    ) {
      return "Configured FPS must be greater than 0 and no more than 240.";
    }

    if (
      width !== null &&
      (
        width <= 0 ||
        !Number.isInteger(width)
      )
    ) {
      return "Resolution width must be a positive whole number.";
    }

    if (
      height !== null &&
      (
        height <= 0 ||
        !Number.isInteger(height)
      )
    ) {
      return "Resolution height must be a positive whole number.";
    }

    return null;
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const validationError =
      validate();

    if (validationError) {
      setError(validationError);
      return;
    }

    setSubmitting(true);
    setError(null);

    const payload:
      CameraCreatePayload = {
      name: form.name.trim(),
      location:
        optionalText(
          form.location,
        ),
      description:
        optionalText(
          form.description,
        ),
      stream_url:
        optionalText(
          form.streamUrl,
        ),
      status: form.status,
      latitude:
        optionalNumber(
          form.latitude,
        ),
      longitude:
        optionalNumber(
          form.longitude,
        ),
      configured_fps:
        optionalNumber(
          form.configuredFps,
        ),
      resolution_width:
        optionalNumber(
          form.resolutionWidth,
        ),
      resolution_height:
        optionalNumber(
          form.resolutionHeight,
        ),
    };

    try {
      const savedCamera =
        camera
          ? await updateCamera(
              camera.id,
              payload,
            )
          : await createCamera({
              ...payload,
              configuration: {},
            });

      onSaved(savedCamera);
      onClose();
    } catch (
      requestError
    ) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Camera could not be saved.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="camera-form-title"
        className="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white shadow-2xl"
      >
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white px-6 py-5">
          <div>
            <h2
              id="camera-form-title"
              className="text-xl font-bold text-slate-950"
            >
              {isEditing
                ? "Edit camera"
                : "Register camera"}
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Configure camera identity,
              connection, and video metadata.
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            aria-label="Close camera form"
            className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 text-slate-500 hover:bg-slate-50"
          >
            <X size={19} />
          </button>
        </header>

        <form
          onSubmit={handleSubmit}
          className="p-6"
        >
          <div className="grid gap-5 md:grid-cols-2">
            <label className="md:col-span-2">
              <span className="text-sm font-semibold text-slate-700">
                Camera name
              </span>

              <input
                required
                minLength={2}
                maxLength={120}
                value={form.name}
                onChange={(event) =>
                  updateField(
                    "name",
                    event.target.value,
                  )
                }
                placeholder="Example: Boston Main Junction"
                className="mt-2 h-11 w-full rounded-xl border border-slate-200 px-4 text-sm outline-none focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
              />
            </label>

            <label>
              <span className="text-sm font-semibold text-slate-700">
                Location
              </span>

              <input
                maxLength={255}
                value={form.location}
                onChange={(event) =>
                  updateField(
                    "location",
                    event.target.value,
                  )
                }
                placeholder="Boston, Massachusetts"
                className="mt-2 h-11 w-full rounded-xl border border-slate-200 px-4 text-sm outline-none focus:border-cyan-400"
              />
            </label>

            <label>
              <span className="text-sm font-semibold text-slate-700">
                Status
              </span>

              <select
                value={form.status}
                onChange={(event) =>
                  updateField(
                    "status",
                    event.target
                      .value as CameraStatus,
                  )
                }
                className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-cyan-400"
              >
                {cameraStatuses.map(
                  (status) => (
                    <option
                      key={status.value}
                      value={status.value}
                    >
                      {status.label}
                    </option>
                  ),
                )}
              </select>
            </label>

            <label className="md:col-span-2">
              <span className="text-sm font-semibold text-slate-700">
                Description
              </span>

              <textarea
                rows={3}
                value={form.description}
                onChange={(event) =>
                  updateField(
                    "description",
                    event.target.value,
                  )
                }
                placeholder="Describe the intersection or monitoring purpose."
                className="mt-2 w-full resize-y rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-cyan-400"
              />
            </label>

            <label className="md:col-span-2">
              <span className="text-sm font-semibold text-slate-700">
                Stream URL
              </span>

              <input
                value={form.streamUrl}
                onChange={(event) =>
                  updateField(
                    "streamUrl",
                    event.target.value,
                  )
                }
                placeholder="rtsp://camera-host/live"
                className="mt-2 h-11 w-full rounded-xl border border-slate-200 px-4 font-mono text-sm outline-none focus:border-cyan-400"
              />

              <p className="mt-2 text-xs text-slate-400">
                Supported schemes: RTSP,
                RTSPS, HTTP, and HTTPS.
              </p>
            </label>

            <label>
              <span className="text-sm font-semibold text-slate-700">
                Latitude
              </span>

              <input
                type="number"
                step="any"
                min="-90"
                max="90"
                value={form.latitude}
                onChange={(event) =>
                  updateField(
                    "latitude",
                    event.target.value,
                  )
                }
                placeholder="42.3601"
                className="mt-2 h-11 w-full rounded-xl border border-slate-200 px-4 text-sm outline-none focus:border-cyan-400"
              />
            </label>

            <label>
              <span className="text-sm font-semibold text-slate-700">
                Longitude
              </span>

              <input
                type="number"
                step="any"
                min="-180"
                max="180"
                value={form.longitude}
                onChange={(event) =>
                  updateField(
                    "longitude",
                    event.target.value,
                  )
                }
                placeholder="-71.0589"
                className="mt-2 h-11 w-full rounded-xl border border-slate-200 px-4 text-sm outline-none focus:border-cyan-400"
              />
            </label>

            <label>
              <span className="text-sm font-semibold text-slate-700">
                Configured FPS
              </span>

              <input
                type="number"
                step="any"
                min="0.1"
                max="240"
                value={form.configuredFps}
                onChange={(event) =>
                  updateField(
                    "configuredFps",
                    event.target.value,
                  )
                }
                placeholder="25"
                className="mt-2 h-11 w-full rounded-xl border border-slate-200 px-4 text-sm outline-none focus:border-cyan-400"
              />
            </label>

            <div className="grid grid-cols-2 gap-3">
              <label>
                <span className="text-sm font-semibold text-slate-700">
                  Width
                </span>

                <input
                  type="number"
                  min="1"
                  step="1"
                  value={
                    form.resolutionWidth
                  }
                  onChange={(event) =>
                    updateField(
                      "resolutionWidth",
                      event.target.value,
                    )
                  }
                  placeholder="1920"
                  className="mt-2 h-11 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-cyan-400"
                />
              </label>

              <label>
                <span className="text-sm font-semibold text-slate-700">
                  Height
                </span>

                <input
                  type="number"
                  min="1"
                  step="1"
                  value={
                    form.resolutionHeight
                  }
                  onChange={(event) =>
                    updateField(
                      "resolutionHeight",
                      event.target.value,
                    )
                  }
                  placeholder="1080"
                  className="mt-2 h-11 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-cyan-400"
                />
              </label>
            </div>
          </div>

          {error ? (
            <div className="mt-5 flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              <AlertCircle
                size={18}
                className="mt-0.5 shrink-0"
              />

              {error}
            </div>
          ) : null}

          <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="h-11 rounded-xl border border-slate-200 px-5 text-sm font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={submitting}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-cyan-500 px-5 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting ? (
                <>
                  <LoaderCircle
                    size={18}
                    className="animate-spin"
                  />
                  Saving camera
                </>
              ) : (
                <>
                  <Save size={18} />
                  {isEditing
                    ? "Save changes"
                    : "Create camera"}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function CameraManager({
  initialResponse,
}: CameraManagerProps) {
  const [
    cameras,
    setCameras,
  ] = useState(
    initialResponse.items,
  );

  const [
    total,
    setTotal,
  ] = useState(
    initialResponse.total,
  );

  const [
    searchValue,
    setSearchValue,
  ] = useState("");

  const [
    statusFilter,
    setStatusFilter,
  ] = useState<
    CameraStatus | ""
  >("");

  const [
    modalOpen,
    setModalOpen,
  ] = useState(false);

  const [
    editingCamera,
    setEditingCamera,
  ] = useState<Camera | null>(
    null,
  );

  const [
    busyCameraId,
    setBusyCameraId,
  ] = useState<string | null>(
    null,
  );


  const [
    cameraPendingDelete,
    setCameraPendingDelete,
  ] = useState<Camera | null>(
    null,
  );

  const [
    cameraDeleteError,
    setCameraDeleteError,
  ] = useState<string | null>(
    null,
  );

  const [
    error,
    setError,
  ] = useState<string | null>(
    null,
  );

  const [
    successMessage,
    setSuccessMessage,
  ] = useState<string | null>(
    null,
  );

  const filteredCameras =
    useMemo(() => {
      const normalizedSearch =
        searchValue
          .trim()
          .toLowerCase();

      return cameras.filter(
        (camera) => {
          if (
            statusFilter &&
            camera.status !==
              statusFilter
          ) {
            return false;
          }

          if (!normalizedSearch) {
            return true;
          }

          return [
            camera.name,
            camera.location,
            camera.description,
            camera.stream_url,
            camera.status,
          ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase()
            .includes(
              normalizedSearch,
            );
        },
      );
    }, [
      cameras,
      searchValue,
      statusFilter,
    ]);

  const activeCount =
    cameras.filter(
      (camera) =>
        camera.status === "active",
    ).length;

  const degradedCount =
    cameras.filter(
      (camera) =>
        camera.status ===
        "degraded",
    ).length;

  const offlineCount =
    cameras.filter(
      (camera) =>
        camera.status ===
        "offline",
    ).length;

  function openCreateModal() {
    setEditingCamera(null);
    setModalOpen(true);
    setError(null);
    setSuccessMessage(null);
  }

  function openEditModal(
    camera: Camera,
  ) {
    setEditingCamera(camera);
    setModalOpen(true);
    setError(null);
    setSuccessMessage(null);
  }

  function handleSaved(
    savedCamera: Camera,
  ) {
    const existing =
      cameras.some(
        (camera) =>
          camera.id ===
          savedCamera.id,
      );

    setCameras((current) =>
      existing
        ? current.map((camera) =>
            camera.id ===
            savedCamera.id
              ? savedCamera
              : camera,
          )
        : [
            savedCamera,
            ...current,
          ],
    );

    if (!existing) {
      setTotal(
        (current) =>
          current + 1,
      );
    }

    setSuccessMessage(
      existing
        ? "Camera updated successfully."
        : "Camera registered successfully.",
    );
  }

  async function toggleCameraStatus(
    camera: Camera,
  ) {
    const nextStatus:
      CameraStatus =
      camera.status === "active"
        ? "inactive"
        : "active";

    setBusyCameraId(camera.id);
    setError(null);
    setSuccessMessage(null);

    try {
      const updated =
        await updateCamera(
          camera.id,
          {
            status: nextStatus,
          },
        );

      setCameras((current) =>
        current.map((item) =>
          item.id === updated.id
            ? updated
            : item,
        ),
      );

      setSuccessMessage(
        nextStatus === "active"
          ? `${camera.name} activated.`
          : `${camera.name} deactivated.`,
      );
    } catch (
      requestError
    ) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Camera status could not be updated.",
      );
    } finally {
      setBusyCameraId(null);
    }
  }

  function removeCamera(
    camera: Camera,
  ) {
    setError(null);
    setSuccessMessage(null);
    setCameraDeleteError(null);
    setCameraPendingDelete(camera);
  }

  function closeCameraDeleteDialog() {
    if (
      cameraPendingDelete &&
      busyCameraId ===
        cameraPendingDelete.id
    ) {
      return;
    }

    setCameraPendingDelete(null);
    setCameraDeleteError(null);
  }

  async function confirmCameraDelete() {
    const camera =
      cameraPendingDelete;

    if (!camera) {
      return;
    }

    setBusyCameraId(camera.id);
    setError(null);
    setSuccessMessage(null);
    setCameraDeleteError(null);

    try {
      await deleteCamera(
        camera.id,
      );

      setCameras((current) =>
        current.filter(
          (item) =>
            item.id !== camera.id,
        ),
      );

      setTotal((current) =>
        Math.max(
          current - 1,
          0,
        ),
      );

      setSuccessMessage(
        `${camera.name} deleted.`,
      );

      setCameraPendingDelete(null);
    } catch (
      requestError
    ) {
      setCameraDeleteError(
        requestError instanceof Error
          ? requestError.message
          : "Camera could not be deleted.",
      );
    } finally {
      setBusyCameraId(null);
    }
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <CameraIcon
            size={21}
            className="text-cyan-700"
          />

          <p className="mt-4 text-sm text-slate-500">
            Registered cameras
          </p>

          <p className="mt-1 text-3xl font-bold text-slate-950">
            {total}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <CheckCircle2
            size={21}
            className="text-emerald-600"
          />

          <p className="mt-4 text-sm text-slate-500">
            Active
          </p>

          <p className="mt-1 text-3xl font-bold text-slate-950">
            {activeCount}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <AlertCircle
            size={21}
            className="text-amber-600"
          />

          <p className="mt-4 text-sm text-slate-500">
            Degraded
          </p>

          <p className="mt-1 text-3xl font-bold text-slate-950">
            {degradedCount}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <Wifi
            size={21}
            className="text-rose-600"
          />

          <p className="mt-4 text-sm text-slate-500">
            Offline
          </p>

          <p className="mt-1 text-3xl font-bold text-slate-950">
            {offlineCount}
          </p>
        </article>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
          <div>
            <h2 className="font-semibold text-slate-950">
              Camera registry
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Manage monitoring cameras and
              open their road-scene settings.
            </p>
          </div>

          <button
            type="button"
            onClick={openCreateModal}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-cyan-500 px-5 text-sm font-semibold text-slate-950 hover:bg-cyan-400"
          >
            <Plus size={18} />
            Register camera
          </button>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-2 lg:grid-cols-[1fr_240px_auto]">
          <label className="relative">
            <Search
              size={18}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />

            <input
              value={searchValue}
              onChange={(event) =>
                setSearchValue(
                  event.target.value,
                )
              }
              placeholder="Search camera, location or stream"
              className="h-11 w-full rounded-xl border border-slate-200 pl-10 pr-4 text-sm outline-none focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
            />
          </label>

          <select
            value={statusFilter}
            onChange={(event) =>
              setStatusFilter(
                event.target
                  .value as
                  | CameraStatus
                  | "",
              )
            }
            className="h-11 rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-cyan-400"
          >
            <option value="">
              All statuses
            </option>

            {cameraStatuses.map(
              (status) => (
                <option
                  key={status.value}
                  value={status.value}
                >
                  {status.label}
                </option>
              ),
            )}
          </select>

          <button
            type="button"
            disabled={
              !searchValue &&
              !statusFilter
            }
            onClick={() => {
              setSearchValue("");
              setStatusFilter("");
            }}
            className="h-11 w-full rounded-xl border border-slate-200 px-4 text-sm font-semibold text-slate-600 lg:w-auto hover:bg-slate-50 disabled:opacity-40"
          >
            Clear
          </button>
        </div>

        {error ? (
          <div className="mt-4 flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            <AlertCircle
              size={18}
              className="mt-0.5 shrink-0"
            />

            {error}
          </div>
        ) : null}

        {successMessage ? (
          <div className="mt-4 flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            <CheckCircle2
              size={18}
              className="mt-0.5 shrink-0"
            />

            {successMessage}
          </div>
        ) : null}
      </section>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {filteredCameras.length ? (
          <>
          <MobileTableNotice />

          <div className="overflow-x-auto overscroll-x-contain touch-pan-x [scrollbar-width:thin]">
            <table className="w-full min-w-[1100px] text-left">
              <thead className="border-b border-slate-200 bg-slate-50">
                <tr className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <th className="px-5 py-4">
                    Camera
                  </th>
                  <th className="px-5 py-4">
                    Status
                  </th>
                  <th className="px-5 py-4">
                    Stream
                  </th>
                  <th className="px-5 py-4">
                    Video settings
                  </th>
                  <th className="px-5 py-4">
                    Updated
                  </th>
                  <th className="px-5 py-4 text-right">
                    Actions
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {filteredCameras.map(
                  (camera) => {
                    const busy =
                      busyCameraId ===
                      camera.id;

                    return (
                      <tr
                        key={camera.id}
                        className="hover:bg-slate-50/70"
                      >
                        <td className="px-5 py-4">
                          <div className="flex items-start gap-3">
                            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-cyan-50 text-cyan-700">
                              <CameraIcon
                                size={20}
                              />
                            </span>

                            <div>
                              <p className="text-sm font-semibold text-slate-950">
                                {camera.name}
                              </p>

                              <p className="mt-1 flex items-center gap-1 text-xs text-slate-400">
                                <MapPin
                                  size={13}
                                />
                                {camera.location ??
                                  "No location"}
                              </p>

                              <p className="mt-1 font-mono text-xs text-slate-400">
                                {camera.id.slice(
                                  0,
                                  12,
                                )}
                              </p>
                            </div>
                          </div>
                        </td>

                        <td className="px-5 py-4">
                          <span
                            className={[
                              "inline-flex rounded-full px-3 py-1 text-xs font-semibold capitalize",
                              statusStyles[
                                camera.status
                              ],
                            ].join(" ")}
                          >
                            {camera.status}
                          </span>
                        </td>

                        <td className="px-5 py-4">
                          <p className="max-w-[230px] truncate font-mono text-xs text-slate-600">
                            {camera.stream_url ??
                              "Not configured"}
                          </p>
                        </td>

                        <td className="px-5 py-4">
                          <p className="text-sm text-slate-700">
                            {camera.resolution_width &&
                            camera.resolution_height
                              ? `${camera.resolution_width} × ${camera.resolution_height}`
                              : "Resolution unavailable"}
                          </p>

                          <p className="mt-1 text-xs text-slate-400">
                            {camera.configured_fps
                              ? `${camera.configured_fps} FPS`
                              : "FPS unavailable"}
                          </p>
                        </td>

                        <td className="px-5 py-4 text-sm text-slate-500">
                          {formatDate(
                            camera.updated_at,
                          )}
                        </td>

                        <td className="px-5 py-4">
                          <div className="flex flex-wrap justify-end gap-2">
                            <Link
                              href={`/cameras/${camera.id}/scene`}
                              className="inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-cyan-200 bg-cyan-50 px-3 text-sm font-semibold text-cyan-800 hover:bg-cyan-100"
                            >
                              <Settings2
                                size={16}
                              />
                              Scene
                            </Link>

                            <button
                              type="button"
                              onClick={() =>
                                openEditModal(
                                  camera,
                                )
                              }
                              disabled={busy}
                              className="inline-flex h-9 items-center justify-center rounded-lg border border-slate-200 px-3 text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                              aria-label={`Edit ${camera.name}`}
                            >
                              <Pencil
                                size={16}
                              />
                            </button>

                            <button
                              type="button"
                              onClick={() =>
                                toggleCameraStatus(
                                  camera,
                                )
                              }
                              disabled={busy}
                              className="inline-flex h-9 items-center justify-center rounded-lg border border-slate-200 px-3 text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                              aria-label={
                                camera.status ===
                                "active"
                                  ? `Deactivate ${camera.name}`
                                  : `Activate ${camera.name}`
                              }
                            >
                              {busy ? (
                                <LoaderCircle
                                  size={16}
                                  className="animate-spin"
                                />
                              ) : (
                                <Power
                                  size={16}
                                />
                              )}
                            </button>

                            <button
                              type="button"
                              onClick={() =>
                                removeCamera(
                                  camera,
                                )
                              }
                              disabled={busy}
                              className="inline-flex h-9 items-center justify-center rounded-lg border border-rose-200 px-3 text-rose-600 hover:bg-rose-50 disabled:opacity-50"
                              aria-label={`Delete ${camera.name}`}
                            >
                              <Trash2
                                size={16}
                              />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  },
                )}
              </tbody>
            </table>
          </div>
          </>
        ) : (
          <div className="px-6 py-16 text-center">
            <CameraIcon
              size={37}
              className="mx-auto text-slate-300"
            />

            <h3 className="mt-4 font-semibold text-slate-950">
              No cameras found
            </h3>

            <p className="mt-2 text-sm text-slate-500">
              Register a camera or clear the
              current filters.
            </p>
          </div>
        )}
      </section>

      {modalOpen ? (
        <CameraFormModal
          camera={editingCamera}
          onClose={() =>
            setModalOpen(false)
          }
          onSaved={handleSaved}
        />
      ) : null}

      <ConfirmDialog
        open={
          cameraPendingDelete !== null
        }
        title="Delete this camera?"
        description={
          cameraPendingDelete
            ? `Delete "${cameraPendingDelete.name}" permanently? Its saved scene configuration will no longer be available. This action cannot be undone.`
            : ""
        }
        confirmLabel="Delete camera"
        variant="danger"
        isLoading={
          Boolean(
            cameraPendingDelete &&
              busyCameraId ===
                cameraPendingDelete.id,
          )
        }
        errorMessage={
          cameraDeleteError
        }
        onConfirm={() => {
          void confirmCameraDelete();
        }}
        onClose={
          closeCameraDeleteDialog
        }
      />
    </div>
  );
}

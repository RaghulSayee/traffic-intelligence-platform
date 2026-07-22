"use client";

import {
  AlertTriangle,
  LoaderCircle,
  X,
} from "lucide-react";
import {
  useEffect,
} from "react";

type ConfirmDialogVariant =
  | "danger"
  | "warning"
  | "default";

type ConfirmDialogProps = {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: ConfirmDialogVariant;
  isLoading?: boolean;
  errorMessage?: string | null;
  onConfirm: () => void;
  onClose: () => void;
};

const confirmButtonStyles: Record<
  ConfirmDialogVariant,
  string
> = {
  danger:
    "bg-rose-600 text-white hover:bg-rose-700",
  warning:
    "bg-amber-500 text-slate-950 hover:bg-amber-400",
  default:
    "bg-cyan-500 text-slate-950 hover:bg-cyan-400",
};

const iconStyles: Record<
  ConfirmDialogVariant,
  string
> = {
  danger:
    "bg-rose-50 text-rose-600",
  warning:
    "bg-amber-50 text-amber-600",
  default:
    "bg-cyan-50 text-cyan-700",
};

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "default",
  isLoading = false,
  errorMessage = null,
  onConfirm,
  onClose,
}: ConfirmDialogProps) {
  useEffect(() => {
    if (!open) {
      return;
    }

    function handleKeyDown(
      event: KeyboardEvent,
    ) {
      if (
        event.key === "Escape" &&
        !isLoading
      ) {
        onClose();
      }
    }

    const previousOverflow =
      document.body.style.overflow;

    document.body.style.overflow =
      "hidden";

    window.addEventListener(
      "keydown",
      handleKeyDown,
    );

    return () => {
      document.body.style.overflow =
        previousOverflow;

      window.removeEventListener(
        "keydown",
        handleKeyDown,
      );
    };
  }, [
    isLoading,
    onClose,
    open,
  ]);

  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/55 px-4 py-8 backdrop-blur-sm"
      role="presentation"
      onMouseDown={(event) => {
        if (
          event.target ===
            event.currentTarget &&
          !isLoading
        ) {
          onClose();
        }
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-description"
        className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl"
      >
        <div className="flex items-start justify-between gap-4">
          <span
            className={[
              "flex h-12 w-12 shrink-0 items-center justify-center rounded-xl",
              iconStyles[variant],
            ].join(" ")}
          >
            <AlertTriangle size={23} />
          </span>

          <button
            type="button"
            aria-label="Close dialog"
            onClick={onClose}
            disabled={isLoading}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <X size={19} />
          </button>
        </div>

        <h2
          id="confirm-dialog-title"
          className="mt-5 text-xl font-bold tracking-tight text-slate-950"
        >
          {title}
        </h2>

        <p
          id="confirm-dialog-description"
          className="mt-2 text-sm leading-6 text-slate-500"
        >
          {description}
        </p>

        {errorMessage ? (
          <div className="mt-5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {errorMessage}
          </div>
        ) : null}

        <div className="mt-7 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            className="inline-flex h-11 items-center justify-center rounded-xl border border-slate-200 bg-white px-5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {cancelLabel}
          </button>

          <button
            type="button"
            onClick={onConfirm}
            disabled={isLoading}
            className={[
              "inline-flex h-11 items-center justify-center gap-2 rounded-xl px-5 text-sm font-semibold disabled:cursor-wait disabled:opacity-60",
              confirmButtonStyles[
                variant
              ],
            ].join(" ")}
          >
            {isLoading ? (
              <LoaderCircle
                size={17}
                className="animate-spin"
              />
            ) : null}

            {isLoading
              ? "Please wait"
              : confirmLabel}
          </button>
        </div>
      </section>
    </div>
  );
}

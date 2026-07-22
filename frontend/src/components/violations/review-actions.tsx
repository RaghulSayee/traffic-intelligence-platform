"use client";

import {
  AlertCircle,
  Check,
  CheckCircle2,
  Clock3,
  LoaderCircle,
  MessageSquareText,
  RotateCcw,
  UserRound,
  X,
  XCircle,
} from "lucide-react";
import {
  useMemo,
  useState,
} from "react";
import { useRouter } from "next/navigation";

import {
  reviewViolation,
} from "@/lib/api/violations";
import type {
  ReviewStatus,
  ViolationEvent,
  ViolationReviewDecision,
  ViolationReviewMetadata,
} from "@/types/violations";

type ReviewActionsProps = {
  violation: ViolationEvent;
};

const statusStyles: Record<
  ReviewStatus,
  string
> = {
  pending:
    "border-amber-200 bg-amber-50 text-amber-700",
  confirmed:
    "border-emerald-200 bg-emerald-50 text-emerald-700",
  rejected:
    "border-rose-200 bg-rose-50 text-rose-700",
};

const statusIcons = {
  pending: Clock3,
  confirmed: CheckCircle2,
  rejected: XCircle,
};

function formatLabel(
  value: string,
): string {
  return value
    .split("_")
    .map(
      (part) =>
        part.charAt(0).toUpperCase() +
        part.slice(1),
    )
    .join(" ");
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
    return value;
  }

  return new Intl.DateTimeFormat(
    "en-US",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  ).format(date);
}

function getReviewMetadata(
  violation: ViolationEvent,
): ViolationReviewMetadata | null {
  const value =
    violation.event_metadata?.review;

  if (
    typeof value !== "object" ||
    value === null
  ) {
    return null;
  }

  const review =
    value as Record<
      string,
      unknown
    >;

  const status =
    review.status;

  const reviewedAt =
    review.reviewed_at;

  if (
    status !== "pending" &&
    status !== "confirmed" &&
    status !== "rejected"
  ) {
    return null;
  }

  if (
    typeof reviewedAt !==
    "string"
  ) {
    return null;
  }

  return {
    status,
    reviewed_at: reviewedAt,
    reviewer:
      typeof review.reviewer ===
      "string"
        ? review.reviewer
        : null,
    note:
      typeof review.note ===
      "string"
        ? review.note
        : null,
  };
}

export function ReviewActions({
  violation,
}: ReviewActionsProps) {
  const router = useRouter();

  const [
    currentViolation,
    setCurrentViolation,
  ] = useState(violation);

  const currentReview =
    useMemo(
      () =>
        getReviewMetadata(
          currentViolation,
        ),
      [currentViolation],
    );

  const initialDecision:
    | ViolationReviewDecision
    | null =
    currentViolation.review_status ===
      "confirmed" ||
    currentViolation.review_status ===
      "rejected"
      ? currentViolation.review_status
      : null;

  const [
    selectedDecision,
    setSelectedDecision,
  ] = useState<
    ViolationReviewDecision | null
  >(initialDecision);

  const [
    reviewer,
    setReviewer,
  ] = useState(
    currentReview?.reviewer ?? "",
  );

  const [
    note,
    setNote,
  ] = useState(
    currentReview?.note ?? "",
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

  const [
    successMessage,
    setSuccessMessage,
  ] = useState<string | null>(
    null,
  );

  const StatusIcon =
    statusIcons[
      currentViolation.review_status
    ];

  const normalizedReviewer =
    reviewer.trim();

  const normalizedNote =
    note.trim();

  const currentReviewer =
    currentReview?.reviewer ?? "";

  const currentNote =
    currentReview?.note ?? "";

  const hasChanges =
    selectedDecision !== null &&
    (
      selectedDecision !==
        currentViolation.review_status ||
      normalizedReviewer !==
        currentReviewer ||
      normalizedNote !==
        currentNote
    );

  const canSubmit =
    selectedDecision !== null &&
    normalizedReviewer.length > 0 &&
    normalizedReviewer.length <=
      120 &&
    normalizedNote.length <=
      2000 &&
    hasChanges &&
    !submitting;

  async function submitReview() {
    if (
      !selectedDecision ||
      !canSubmit
    ) {
      return;
    }

    setSubmitting(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const updatedViolation =
        await reviewViolation(
          currentViolation.id,
          {
            review_status:
              selectedDecision,
            reviewer:
              normalizedReviewer ||
              null,
            note:
              normalizedNote ||
              null,
          },
        );

      setCurrentViolation(
        updatedViolation,
      );

      setSuccessMessage(
        selectedDecision ===
          "confirmed"
          ? "Violation confirmed successfully."
          : "Violation rejected successfully.",
      );

      router.refresh();
    } catch (
      requestError
    ) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The review could not be saved.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  function resetForm() {
    const latestReview =
      getReviewMetadata(
        currentViolation,
      );

    setSelectedDecision(
      currentViolation.review_status ===
        "confirmed" ||
      currentViolation.review_status ===
        "rejected"
        ? currentViolation.review_status
        : null,
    );

    setReviewer(
      latestReview?.reviewer ?? "",
    );

    setNote(
      latestReview?.note ?? "",
    );

    setError(null);
    setSuccessMessage(null);
  }

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h2 className="font-semibold text-slate-950">
            Human review
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            Confirm or reject the detected
            traffic violation.
          </p>
        </div>

        <span
          className={[
            "inline-flex w-fit items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold",
            statusStyles[
              currentViolation
                .review_status
            ],
          ].join(" ")}
        >
          <StatusIcon size={15} />

          {formatLabel(
            currentViolation
              .review_status,
          )}
        </span>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <button
          type="button"
          disabled={submitting}
          onClick={() => {
            setSelectedDecision(
              "confirmed",
            );

            setError(null);
            setSuccessMessage(null);
          }}
          className={[
            "flex min-h-24 items-center gap-3 rounded-xl border p-4 text-left transition",
            selectedDecision ===
            "confirmed"
              ? "border-emerald-400 bg-emerald-50 ring-4 ring-emerald-100"
              : "border-slate-200 hover:border-emerald-300 hover:bg-emerald-50/40",
            submitting
              ? "cursor-not-allowed opacity-60"
              : "",
          ].join(" ")}
        >
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
            <Check size={22} />
          </span>

          <span>
            <span className="block text-sm font-semibold text-slate-950">
              Confirm violation
            </span>

            <span className="mt-1 block text-xs leading-5 text-slate-500">
              Evidence supports the detected
              traffic violation.
            </span>
          </span>
        </button>

        <button
          type="button"
          disabled={submitting}
          onClick={() => {
            setSelectedDecision(
              "rejected",
            );

            setError(null);
            setSuccessMessage(null);
          }}
          className={[
            "flex min-h-24 items-center gap-3 rounded-xl border p-4 text-left transition",
            selectedDecision ===
            "rejected"
              ? "border-rose-400 bg-rose-50 ring-4 ring-rose-100"
              : "border-slate-200 hover:border-rose-300 hover:bg-rose-50/40",
            submitting
              ? "cursor-not-allowed opacity-60"
              : "",
          ].join(" ")}
        >
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-rose-100 text-rose-700">
            <X size={22} />
          </span>

          <span>
            <span className="block text-sm font-semibold text-slate-950">
              Reject violation
            </span>

            <span className="mt-1 block text-xs leading-5 text-slate-500">
              Detection is incorrect or the
              evidence is insufficient.
            </span>
          </span>
        </button>
      </div>

      <div className="mt-5">
        <label
          htmlFor="reviewer"
          className="text-sm font-semibold text-slate-700"
        >
          Reviewer
        </label>

        <div className="relative mt-2">
          <UserRound
            size={18}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
          />

          <input
            id="reviewer"
            value={reviewer}
            disabled={submitting}
            maxLength={120}
            onChange={(event) => {
              setReviewer(
                event.target.value,
              );

              setError(null);
              setSuccessMessage(null);
            }}
            placeholder="Enter reviewer name"
            className="h-11 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-4 text-sm outline-none focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100 disabled:bg-slate-50"
          />
        </div>

        {!normalizedReviewer ? (
          <p className="mt-2 text-xs text-amber-600">
            Reviewer name is required for the
            audit record.
          </p>
        ) : null}
      </div>

      <div className="mt-5">
        <div className="flex items-center justify-between gap-3">
          <label
            htmlFor="review-note"
            className="flex items-center gap-2 text-sm font-semibold text-slate-700"
          >
            <MessageSquareText
              size={17}
            />

            Review note
          </label>

          <span
            className={[
              "text-xs",
              note.length > 2000
                ? "text-rose-600"
                : "text-slate-400",
            ].join(" ")}
          >
            {note.length}/2000
          </span>
        </div>

        <textarea
          id="review-note"
          value={note}
          disabled={submitting}
          maxLength={2000}
          rows={5}
          onChange={(event) => {
            setNote(
              event.target.value,
            );

            setError(null);
            setSuccessMessage(null);
          }}
          placeholder="Explain why this violation was confirmed or rejected."
          className="mt-2 w-full resize-y rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm leading-6 outline-none focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100 disabled:bg-slate-50"
        />
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

      <div className="mt-5 flex flex-col gap-3 sm:flex-row">
        <button
          type="button"
          onClick={submitReview}
          disabled={!canSubmit}
          className="inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-xl bg-cyan-500 px-5 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? (
            <>
              <LoaderCircle
                size={18}
                className="animate-spin"
              />

              Saving review
            </>
          ) : (
            <>
              <CheckCircle2
                size={18}
              />

              Save review
            </>
          )}
        </button>

        <button
          type="button"
          onClick={resetForm}
          disabled={submitting}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-slate-200 px-5 text-sm font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50"
        >
          <RotateCcw size={17} />
          Reset
        </button>
      </div>

      {!hasChanges &&
      selectedDecision ? (
        <p className="mt-3 text-center text-xs text-slate-400">
          Change the decision, reviewer, or
          note to enable saving.
        </p>
      ) : null}

      {currentReview ? (
        <section className="mt-6 border-t border-slate-200 pt-5">
          <h3 className="text-sm font-semibold text-slate-950">
            Latest review record
          </h3>

          <dl className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Decision
              </dt>

              <dd className="mt-1 text-sm text-slate-700">
                {formatLabel(
                  currentReview.status,
                )}
              </dd>
            </div>

            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Reviewed at
              </dt>

              <dd className="mt-1 text-sm text-slate-700">
                {formatDate(
                  currentReview.reviewed_at,
                )}
              </dd>
            </div>

            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Reviewer
              </dt>

              <dd className="mt-1 text-sm text-slate-700">
                {currentReview.reviewer ??
                  "Not provided"}
              </dd>
            </div>

            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Note
              </dt>

              <dd className="mt-1 whitespace-pre-wrap text-sm text-slate-700">
                {currentReview.note ??
                  "No note provided"}
              </dd>
            </div>
          </dl>
        </section>
      ) : null}
    </article>
  );
}

"use client";

import {
  LoaderCircle,
  Trash2,
} from "lucide-react";
import {
  useRouter,
} from "next/navigation";
import {
  useCallback,
  useState,
} from "react";

import {
  ConfirmDialog,
} from "@/components/ui/confirm-dialog";
import {
  deleteVideo,
} from "@/lib/api/resources";

type DeleteVideoButtonProps = {
  videoId: string;
  disabled?: boolean;
};

export function DeleteVideoButton({
  videoId,
  disabled = false,
}: DeleteVideoButtonProps) {
  const router = useRouter();

  const [
    dialogOpen,
    setDialogOpen,
  ] = useState(false);

  const [
    isDeleting,
    setIsDeleting,
  ] = useState(false);

  const [
    errorMessage,
    setErrorMessage,
  ] = useState<string | null>(
    null,
  );

  function openDialog() {
    if (disabled) {
      return;
    }

    setErrorMessage(null);
    setDialogOpen(true);
  }

  const closeDialog =
    useCallback(() => {
      if (isDeleting) {
        return;
      }

      setDialogOpen(false);
      setErrorMessage(null);
    }, [
      isDeleting,
    ]);

  async function handleDelete() {
    setIsDeleting(true);
    setErrorMessage(null);

    try {
      await deleteVideo(videoId);

      setDialogOpen(false);
      router.refresh();
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "The video could not be deleted.",
      );
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={openDialog}
        disabled={
          disabled ||
          isDeleting
        }
        title={
          disabled
            ? "Videos with queued or running jobs cannot be deleted."
            : "Delete video"
        }
        className="inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 text-sm font-semibold text-rose-700 hover:bg-rose-100 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
      >
        {isDeleting ? (
          <LoaderCircle
            size={16}
            className="animate-spin"
          />
        ) : (
          <Trash2 size={16} />
        )}

        Delete
      </button>

      <ConfirmDialog
        open={dialogOpen}
        title="Delete this video?"
        description="This permanently removes the uploaded video, processing jobs, detected violations, previews, and generated evidence. This action cannot be undone."
        confirmLabel="Delete video"
        variant="danger"
        isLoading={isDeleting}
        errorMessage={errorMessage}
        onConfirm={() => {
          void handleDelete();
        }}
        onClose={closeDialog}
      />
    </>
  );
}

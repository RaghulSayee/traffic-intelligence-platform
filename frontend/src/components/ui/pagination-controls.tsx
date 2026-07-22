"use client";

import {
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

type PaginationControlsProps = {
  currentPage: number;
  totalPages: number;
  pageSize: number;
  totalItems: number;
  startItem: number;
  endItem: number;
  disabled?: boolean;
  onPageChange: (
    page: number,
  ) => void;
  onPageSizeChange: (
    pageSize: number,
  ) => void;
};

const pageSizeOptions = [
  5,
  10,
  20,
  50,
];

export function PaginationControls({
  currentPage,
  totalPages,
  pageSize,
  totalItems,
  startItem,
  endItem,
  disabled = false,
  onPageChange,
  onPageSizeChange,
}: PaginationControlsProps) {
  const previousDisabled =
    disabled ||
    currentPage <= 1;

  const nextDisabled =
    disabled ||
    currentPage >= totalPages;

  return (
    <div className="flex flex-col gap-4 border-t border-slate-200 bg-slate-50/70 px-4 py-4 sm:px-5 md:flex-row md:items-center md:justify-between">
      <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-slate-500 sm:justify-start">
        <span>
          Showing{" "}
          <strong className="font-semibold text-slate-900">
            {startItem}
          </strong>
          {" – "}
          <strong className="font-semibold text-slate-900">
            {endItem}
          </strong>
          {" of "}
          <strong className="font-semibold text-slate-900">
            {totalItems}
          </strong>
        </span>

        <label className="flex items-center gap-2">
          <span>
            Rows
          </span>

          <select
            value={pageSize}
            disabled={disabled}
            onChange={(event) =>
              onPageSizeChange(
                Number(
                  event.target.value,
                ),
              )
            }
            aria-label="Rows per page"
            className="h-9 rounded-lg border border-slate-200 bg-white px-2 text-sm font-medium text-slate-700 outline-none focus:border-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {pageSizeOptions.map(
              (option) => (
                <option
                  key={option}
                  value={option}
                >
                  {option}
                </option>
              ),
            )}
          </select>
        </label>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between md:justify-end">
        <span className="text-center text-sm font-medium text-slate-600 sm:text-left">
          Page{" "}
          {currentPage} of{" "}
          {totalPages}
        </span>

        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={
              previousDisabled
            }
            onClick={() =>
              onPageChange(
                currentPage - 1,
              )
            }
            aria-label="Previous page"
            className="inline-flex h-10 flex-1 items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 hover:border-cyan-300 hover:bg-cyan-50 disabled:cursor-not-allowed disabled:opacity-40 sm:flex-none"
          >
            <ChevronLeft
              size={16}
            />

            Previous
          </button>

          <button
            type="button"
            disabled={
              nextDisabled
            }
            onClick={() =>
              onPageChange(
                currentPage + 1,
              )
            }
            aria-label="Next page"
            className="inline-flex h-10 flex-1 items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 hover:border-cyan-300 hover:bg-cyan-50 disabled:cursor-not-allowed disabled:opacity-40 sm:flex-none"
          >
            Next

            <ChevronRight
              size={16}
            />
          </button>
        </div>
      </div>
    </div>
  );
}

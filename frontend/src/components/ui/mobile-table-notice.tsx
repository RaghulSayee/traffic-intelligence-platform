import {
  MoveHorizontal,
} from "lucide-react";

export function MobileTableNotice() {
  return (
    <div className="flex items-center gap-2 border-b border-slate-100 bg-slate-50 px-4 py-2 text-xs text-slate-500 md:hidden">
      <MoveHorizontal
        size={15}
        className="shrink-0 text-cyan-700"
      />

      Swipe horizontally to view all table columns.
    </div>
  );
}

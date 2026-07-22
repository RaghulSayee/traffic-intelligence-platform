import type {
  ReactNode,
} from "react";

type PageHeaderProps = {
  eyebrow?: string;
  title: string;
  description: string;
  action?: ReactNode;
};

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: PageHeaderProps) {
  return (
    <section className="mb-7 flex min-w-0 flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div className="min-w-0">
        {eyebrow ? (
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-cyan-700">
            {eyebrow}
          </p>
        ) : null}

        <h2 className="break-words text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">
          {title}
        </h2>

        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
          {description}
        </p>
      </div>

      {action ? (
        <div className="w-full shrink-0 [&>*]:w-full sm:w-auto sm:[&>*]:w-auto">
          {action}
        </div>
      ) : null}
    </section>
  );
}

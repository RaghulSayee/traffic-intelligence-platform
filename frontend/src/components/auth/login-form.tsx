"use client";

import {
  Activity,
  Eye,
  EyeOff,
  LoaderCircle,
  LockKeyhole,
  Mail,
} from "lucide-react";
import {
  useRouter,
} from "next/navigation";
import {
  FormEvent,
  useState,
} from "react";

type ErrorResponse = {
  detail?: unknown;
};

export function LoginForm() {
  const router = useRouter();

  const [
    email,
    setEmail,
  ] = useState("");

  const [
    password,
    setPassword,
  ] = useState("");

  const [
    passwordVisible,
    setPasswordVisible,
  ] = useState(false);

  const [
    isSubmitting,
    setIsSubmitting,
  ] = useState(false);

  const [
    errorMessage,
    setErrorMessage,
  ] = useState<string | null>(
    null,
  );

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const response = await fetch(
        "/api/auth/login",
        {
          method: "POST",
          headers: {
            Accept:
              "application/json",
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            email,
            password,
          }),
        },
      );

      const payload =
        (await response.json()) as
          ErrorResponse;

      if (!response.ok) {
        throw new Error(
          typeof payload.detail ===
            "string"
            ? payload.detail
            : "Login failed.",
        );
      }

      router.replace(
        "/dashboard",
      );

      router.refresh();
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Login failed.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="w-full max-w-md">
      <div className="mb-8 flex items-center justify-center gap-3">
        <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-cyan-500 text-slate-950 shadow-lg shadow-cyan-500/20">
          <Activity
            size={26}
            strokeWidth={2.4}
          />
        </span>

        <div>
          <p className="font-bold text-white">
            Traffic Intelligence
          </p>

          <p className="text-xs text-slate-400">
            Violation monitoring platform
          </p>
        </div>
      </div>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-700">
          Secure access
        </p>

        <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">
          Sign in to your account
        </h1>

        <p className="mt-2 text-sm leading-6 text-slate-500">
          Enter your administrator or
          reviewer credentials.
        </p>

        <form
          onSubmit={handleSubmit}
          className="mt-7 space-y-5"
        >
          <label className="block">
            <span className="text-sm font-semibold text-slate-700">
              Email address
            </span>

            <span className="relative mt-2 flex items-center">
              <Mail
                size={18}
                className="pointer-events-none absolute left-3 text-slate-400"
              />

              <input
                type="email"
                value={email}
                onChange={(event) =>
                  setEmail(
                    event.target.value,
                  )
                }
                required
                autoComplete="email"
                placeholder="raghul@example.com"
                className="h-12 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-4 text-sm text-slate-950 outline-none focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
              />
            </span>
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-slate-700">
              Password
            </span>

            <span className="relative mt-2 flex items-center">
              <LockKeyhole
                size={18}
                className="pointer-events-none absolute left-3 text-slate-400"
              />

              <input
                type={
                  passwordVisible
                    ? "text"
                    : "password"
                }
                value={password}
                onChange={(event) =>
                  setPassword(
                    event.target.value,
                  )
                }
                required
                minLength={8}
                autoComplete="current-password"
                placeholder="Enter your password"
                className="h-12 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-11 text-sm text-slate-950 outline-none focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
              />

              <button
                type="button"
                onClick={() =>
                  setPasswordVisible(
                    (current) =>
                      !current,
                  )
                }
                aria-label={
                  passwordVisible
                    ? "Hide password"
                    : "Show password"
                }
                className="absolute right-3 text-slate-400 hover:text-slate-700"
              >
                {passwordVisible ? (
                  <EyeOff size={18} />
                ) : (
                  <Eye size={18} />
                )}
              </button>
            </span>
          </label>

          {errorMessage ? (
            <div
              role="alert"
              className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
            >
              {errorMessage}
            </div>
          ) : null}

          <button
            type="submit"
            disabled={isSubmitting}
            className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-cyan-500 px-5 text-sm font-bold text-slate-950 hover:bg-cyan-400 disabled:cursor-wait disabled:opacity-60"
          >
            {isSubmitting ? (
              <LoaderCircle
                size={18}
                className="animate-spin"
              />
            ) : null}

            {isSubmitting
              ? "Signing in"
              : "Sign in"}
          </button>
        </form>
      </section>
    </div>
  );
}

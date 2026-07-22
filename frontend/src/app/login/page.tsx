import {
  redirect,
} from "next/navigation";

import {
  LoginForm,
} from "@/components/auth/login-form";
import {
  getCurrentUser,
} from "@/lib/auth/server";

export const dynamic =
  "force-dynamic";

export default async function LoginPage() {
  const user =
    await getCurrentUser();

  if (user) {
    redirect("/dashboard");
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-12">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute left-1/2 top-[-18rem] h-[34rem] w-[34rem] -translate-x-1/2 rounded-full bg-cyan-500/10 blur-3xl" />

        <div className="absolute bottom-[-16rem] right-[-10rem] h-[30rem] w-[30rem] rounded-full bg-blue-500/10 blur-3xl" />
      </div>

      <div className="relative z-10 flex w-full justify-center">
        <LoginForm />
      </div>
    </main>
  );
}

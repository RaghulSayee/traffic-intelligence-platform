import "server-only";

import {
  cookies,
} from "next/headers";
import {
  redirect,
} from "next/navigation";

import {
  getBackendApiBaseUrl,
} from "@/lib/auth/backend";
import {
  AUTH_COOKIE_NAME,
} from "@/lib/auth/constants";
import type {
  AuthUser,
} from "@/lib/auth/types";

export async function getCurrentUser(): Promise<
  AuthUser | null
> {
  const cookieStore =
    await cookies();

  const accessToken =
    cookieStore.get(
      AUTH_COOKIE_NAME,
    )?.value;

  if (!accessToken) {
    return null;
  }

  try {
    const response = await fetch(
      `${getBackendApiBaseUrl()}/auth/me`,
      {
        method: "GET",
        headers: {
          Accept:
            "application/json",
          Authorization:
            `Bearer ${accessToken}`,
        },
        cache: "no-store",
      },
    );

    if (!response.ok) {
      return null;
    }

    return (
      await response.json()
    ) as AuthUser;
  } catch {
    return null;
  }
}

export async function requireCurrentUser(): Promise<
  AuthUser
> {
  const user =
    await getCurrentUser();

  if (!user) {
    redirect("/login");
  }

  return user;
}

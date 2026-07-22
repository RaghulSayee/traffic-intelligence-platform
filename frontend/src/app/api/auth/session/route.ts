import {
  cookies,
} from "next/headers";
import {
  NextResponse,
} from "next/server";

import {
  getBackendApiBaseUrl,
} from "@/lib/auth/backend";
import {
  AUTH_COOKIE_NAME,
} from "@/lib/auth/constants";
import type {
  AuthUser,
} from "@/lib/auth/types";

export async function GET() {
  const cookieStore =
    await cookies();

  const accessToken =
    cookieStore.get(
      AUTH_COOKIE_NAME,
    )?.value;

  if (!accessToken) {
    return NextResponse.json(
      {
        detail:
          "Authentication is required.",
      },
      {
        status: 401,
      },
    );
  }

  try {
    const response = await fetch(
      `${getBackendApiBaseUrl()}/auth/me`,
      {
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
      cookieStore.delete(
        AUTH_COOKIE_NAME,
      );

      return NextResponse.json(
        {
          detail:
            "The session is invalid or expired.",
        },
        {
          status: 401,
        },
      );
    }

    const user =
      (await response.json()) as
        AuthUser;

    return NextResponse.json({
      user,
    });
  } catch {
    return NextResponse.json(
      {
        detail:
          "Unable to verify the session.",
      },
      {
        status: 503,
      },
    );
  }
}

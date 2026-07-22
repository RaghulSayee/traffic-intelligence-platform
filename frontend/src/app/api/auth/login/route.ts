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

type BackendLoginResponse = {
  access_token?: unknown;
  expires_in_seconds?: unknown;
  user?: unknown;
  detail?: unknown;
};

export async function POST(
  request: Request,
) {
  let credentials: {
    email?: unknown;
    password?: unknown;
  };

  try {
    credentials =
      (await request.json()) as {
        email?: unknown;
        password?: unknown;
      };
  } catch {
    return NextResponse.json(
      {
        detail:
          "A valid login request is required.",
      },
      {
        status: 400,
      },
    );
  }

  if (
    typeof credentials.email !==
      "string" ||
    typeof credentials.password !==
      "string"
  ) {
    return NextResponse.json(
      {
        detail:
          "Email and password are required.",
      },
      {
        status: 400,
      },
    );
  }

  let backendResponse: Response;

  try {
    backendResponse = await fetch(
      `${getBackendApiBaseUrl()}/auth/login`,
      {
        method: "POST",
        headers: {
          Accept:
            "application/json",
          "Content-Type":
            "application/json",
        },
        body: JSON.stringify({
          email:
            credentials.email,
          password:
            credentials.password,
        }),
        cache: "no-store",
      },
    );
  } catch {
    return NextResponse.json(
      {
        detail:
          "Unable to connect to the authentication server.",
      },
      {
        status: 503,
      },
    );
  }

  let payload: BackendLoginResponse =
    {};

  try {
    payload =
      (await backendResponse.json()) as
        BackendLoginResponse;
  } catch {
    // Preserve the default payload.
  }

  if (!backendResponse.ok) {
    return NextResponse.json(
      {
        detail:
          typeof payload.detail ===
            "string"
            ? payload.detail
            : "Login failed.",
      },
      {
        status:
          backendResponse.status,
      },
    );
  }

  if (
    typeof payload.access_token !==
      "string" ||
    typeof payload.expires_in_seconds !==
      "number" ||
    typeof payload.user !==
      "object" ||
    payload.user === null
  ) {
    return NextResponse.json(
      {
        detail:
          "The authentication server returned an invalid response.",
      },
      {
        status: 502,
      },
    );
  }

  const cookieStore =
    await cookies();

  cookieStore.set(
    AUTH_COOKIE_NAME,
    payload.access_token,
    {
      httpOnly: true,
      secure:
        process.env.NODE_ENV ===
        "production",
      sameSite: "lax",
      path: "/",
      maxAge:
        payload.expires_in_seconds,
    },
  );

  return NextResponse.json({
    user:
      payload.user as AuthUser,
  });
}

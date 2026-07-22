import {
  NextRequest,
  NextResponse,
} from "next/server";

const AUTH_COOKIE_NAME =
  "traffic_access_token";

export function proxy(
  request: NextRequest,
) {
  const accessToken =
    request.cookies.get(
      AUTH_COOKIE_NAME,
    )?.value;

  if (!accessToken) {
    const loginUrl =
      request.nextUrl.clone();

    loginUrl.pathname =
      "/login";

    loginUrl.searchParams.set(
      "next",
      request.nextUrl.pathname,
    );

    return NextResponse.redirect(
      loginUrl,
    );
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/videos/:path*",
    "/jobs/:path*",
    "/cameras/:path*",
    "/violations/:path*",
    "/analytics/:path*",
  ],
};

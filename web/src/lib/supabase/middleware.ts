import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value),
          );
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options),
          );
        },
      },
    },
  );

  // Refreshes the auth token if expired. Must be called on every request
  // so the session stays alive for the full browser session, not just
  // the default 1-hour JWT window.
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // If the user is not signed in and is trying to access a protected route,
  // redirect them to the login page.
  const isAuthRoute =
    request.nextUrl.pathname.startsWith("/login") ||
    request.nextUrl.pathname.startsWith("/setup") ||
    request.nextUrl.pathname.startsWith("/403");

  if (!user && !isAuthRoute) {
    const url = new URL("/login", request.url);
    url.searchParams.set("expired", "1");
    return NextResponse.redirect(url);
  }

  return supabaseResponse;
}

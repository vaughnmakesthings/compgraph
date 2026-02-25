// This file configures the initialization of Sentry on the client.
// The added config here will be used whenever a users loads a page in their browser.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: "https://253ccf02a215dc566c1524382ccd852d@o4510948588847104.ingest.us.sentry.io/4510948590157824",

  // Add optional integrations for additional features
  integrations: [Sentry.replayIntegration()],

  // Sample 20% of traces in production, 100% in development
  tracesSampleRate: process.env.NODE_ENV === "production" ? 0.2 : 1.0,

  // Capture 10% of sessions for Replay, 100% on error
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
});

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;

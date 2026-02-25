// This file configures the initialization of Sentry for edge features (middleware, edge routes, and so on).
// The config you add here will be used whenever one of the edge features is loaded.
// Note that this config is unrelated to the Vercel Edge Runtime and is also required when running locally.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: "https://253ccf02a215dc566c1524382ccd852d@o4510948588847104.ingest.us.sentry.io/4510948590157824",

  // Sample 20% of traces in production, 100% in development
  tracesSampleRate: process.env.NODE_ENV === "production" ? 0.2 : 1.0,

  // Setting this option to true will print useful information to the console while you're setting up Sentry.
  debug: false,
});

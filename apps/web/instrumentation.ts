import * as Sentry from "@sentry/nextjs";

export function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    Sentry.init({
      dsn: process.env.SENTRY_DSN || process.env.NEXT_PUBLIC_SENTRY_DSN,
      tracesSampleRate: 0.1,
      debug: false,
      sendDefaultPii: false,
      beforeSend(event) {
        if (event.request) {
          if (event.request.headers) {
            if (event.request.headers['authorization']) event.request.headers['authorization'] = '[Filtered]';
            if (event.request.headers['cookie']) event.request.headers['cookie'] = '[Filtered]';
          }
          if (event.request.data) {
            event.request.data = '[Filtered payload]';
          }
        }
        return event;
      },
    });
  }

  if (process.env.NEXT_RUNTIME === "edge") {
    Sentry.init({
      dsn: process.env.SENTRY_DSN || process.env.NEXT_PUBLIC_SENTRY_DSN,
      tracesSampleRate: 0.1,
      debug: false,
      sendDefaultPii: false,
      beforeSend(event) {
        if (event.request) {
          if (event.request.headers) {
            if (event.request.headers['authorization']) event.request.headers['authorization'] = '[Filtered]';
            if (event.request.headers['cookie']) event.request.headers['cookie'] = '[Filtered]';
          }
          if (event.request.data) {
            event.request.data = '[Filtered payload]';
          }
        }
        return event;
      },
    });
  }
}

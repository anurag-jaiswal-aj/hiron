import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
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

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;


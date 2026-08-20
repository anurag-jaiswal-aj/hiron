/**
 * Reusable HTTP API Client for Hiron Web Frontend per Engineering Guidelines §4.5 & API Contract §6–9.
 */

export interface ErrorDetail {
  field?: string | null;
  message: string;
  value?: unknown;
}

export interface ErrorBody {
  code: string;
  message: string;
  details?: ErrorDetail[] | null;
  requestId?: string | null;
}

export interface ErrorEnvelope {
  error: ErrorBody;
}

export interface ResponseEnvelope<T> {
  data: T;
}

export interface PaginationMeta {
  hasMore: boolean;
  nextCursor?: string | null;
  totalCount?: number | null;
}

export interface PaginatedResponseEnvelope<T> {
  data: T[];
  pagination: PaginationMeta;
}

export class ApiError extends Error {
  public readonly status: number;
  public readonly code: string;
  public readonly details?: ErrorDetail[] | null;
  public readonly requestId?: string | null;

  constructor(status: number, errorBody: Partial<ErrorBody>) {
    super(errorBody.message || `HTTP Error ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.code = errorBody.code || "UNKNOWN_ERROR";
    this.details = errorBody.details || null;
    this.requestId = errorBody.requestId || null;
  }
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  params?: Record<string, string | number | boolean | null | undefined>;
  body?: unknown;
  skipAuth?: boolean;
  _isRetry?: boolean;
}

const isBrowser = typeof window !== "undefined";

let inMemoryAccessToken: string | null = null;
let isRefreshing = false;
let refreshSubscribers: Array<(token: string | null) => void> = [];
let onUnauthorizedCallback: (() => void) | null = null;

export const setAccessToken = (token: string | null): void => {
  if (!isBrowser) {
    throw new Error("setAccessToken is browser-only and cannot be used in server execution");
  }
  inMemoryAccessToken = token;
};

export const getAccessToken = (): string | null => {
  if (!isBrowser) {
    return null;
  }
  return inMemoryAccessToken;
};

export const setOnUnauthorized = (callback: (() => void) | null): void => {
  if (!isBrowser) {
    throw new Error("setOnUnauthorized is browser-only and cannot be used in server execution");
  }
  onUnauthorizedCallback = callback;
};

const getApiBaseUrl = (): string => {
  if (process.env.NEXT_PUBLIC_API_URL !== undefined) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  return isBrowser ? "" : "http://localhost:8000";
};

function onTokenRefreshed(newToken: string | null): void {
  refreshSubscribers.forEach((callback) => callback(newToken));
  refreshSubscribers = [];
}

export async function apiFetch<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const {
    params,
    body,
    headers: customHeaders,
    skipAuth = false,
    _isRetry = false,
    ...fetchOptions
  } = options;

  let url =
    endpoint.startsWith("http://") || endpoint.startsWith("https://")
      ? endpoint
      : `${getApiBaseUrl()}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;

  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += (url.includes("?") ? "&" : "?") + queryString;
    }
  }

  const headers = new Headers(customHeaders);

  if (body !== undefined && !(body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const currentAccessToken = isBrowser ? inMemoryAccessToken : null;
  if (!skipAuth && currentAccessToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${currentAccessToken}`);
  }

  const requestInit: RequestInit = {
    ...fetchOptions,
    headers,
    credentials: "include",
    body: body !== undefined ? (body instanceof FormData ? body : JSON.stringify(body)) : undefined,
  };

  try {
    const response = await fetch(url, requestInit);

    if (response.status === 204) {
      return undefined as unknown as T;
    }

    const contentType = response.headers.get("content-type");
    const isJson = contentType && contentType.includes("application/json");

    if (response.ok) {
      if (isJson) {
        return (await response.json()) as T;
      }
      return (await response.text()) as unknown as T;
    }

    let errorBody: Partial<ErrorBody> = {};
    if (isJson) {
      try {
        const jsonPayload = await response.json();
        if (jsonPayload && typeof jsonPayload === "object") {
          if ("error" in jsonPayload && jsonPayload.error) {
            errorBody = jsonPayload.error as Partial<ErrorBody>;
          } else {
            errorBody = jsonPayload as Partial<ErrorBody>;
          }
        }
      } catch {
        // Fallback to default error body
      }
    }

    const isAuthEndpoint =
      endpoint.includes("/api/v1/auth/login") ||
      endpoint.includes("/api/v1/auth/refresh") ||
      endpoint.includes("/api/v1/auth/logout");

    if (response.status === 401 && !isAuthEndpoint && !_isRetry && isBrowser) {
      if (!isRefreshing) {
        isRefreshing = true;
        try {
          const refreshResult = await apiFetch<ResponseEnvelope<{ accessToken: string }>>(
            "/api/v1/auth/refresh",
            {
              method: "POST",
              skipAuth: true,
              _isRetry: true,
            },
          );

          const newAccessToken = refreshResult.data.accessToken;
          setAccessToken(newAccessToken);
          isRefreshing = false;
          onTokenRefreshed(newAccessToken);

          // R1 (refresh owner) retries its original request directly once
          return apiFetch<T>(endpoint, {
            ...options,
            _isRetry: true,
          });
        } catch (refreshErr) {
          isRefreshing = false;
          setAccessToken(null);
          onTokenRefreshed(null);
          if (onUnauthorizedCallback) {
            onUnauthorizedCallback();
          }
          throw new ApiError(response.status, errorBody);
        }
      }

      // R2, R3, etc (concurrent requests) subscribe and wait for refresh completion
      const newAccessToken = await new Promise<string | null>((resolve) => {
        refreshSubscribers.push(resolve);
      });

      if (newAccessToken) {
        return apiFetch<T>(endpoint, {
          ...options,
          _isRetry: true,
        });
      }
    }

    throw new ApiError(response.status, errorBody);
  } catch (err) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(500, {
      code: "NETWORK_ERROR",
      message: err instanceof Error ? err.message : "Network error occurred",
    });
  }
}

export const httpClient = {
  get: <T>(endpoint: string, options?: RequestOptions): Promise<T> =>
    apiFetch<T>(endpoint, { ...options, method: "GET" }),

  post: <T>(endpoint: string, body?: unknown, options?: RequestOptions): Promise<T> =>
    apiFetch<T>(endpoint, { ...options, method: "POST", body }),

  put: <T>(endpoint: string, body?: unknown, options?: RequestOptions): Promise<T> =>
    apiFetch<T>(endpoint, { ...options, method: "PUT", body }),

  patch: <T>(endpoint: string, body?: unknown, options?: RequestOptions): Promise<T> =>
    apiFetch<T>(endpoint, { ...options, method: "PATCH", body }),

  delete: <T>(endpoint: string, options?: RequestOptions): Promise<T> =>
    apiFetch<T>(endpoint, { ...options, method: "DELETE" }),
};

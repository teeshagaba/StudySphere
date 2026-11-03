"use client";

import { useCallback, useEffect, useState } from "react";

export const TOKEN_KEY = "studyos_token";

// Empty = same-origin; next.config.mjs rewrites /api to the backend.
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export async function api<T = unknown>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem(TOKEN_KEY)
      : null;

  const headers = new Headers(init.headers);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (
    typeof init.body === "string" &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE}/api${path}`, {
    ...init,
    headers,
  });

  if (res.status === 401 && !path.startsWith("/auth/login")) {
    localStorage.removeItem(TOKEN_KEY);
    window.location.href = "/login";
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));

    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : `Request failed (${res.status})`
    );
  }

  return (res.status === 204
    ? undefined
    : await res.json()) as T;
}

const withBody =
  (method: string) =>
  <T = unknown>(path: string, body?: unknown) =>
    api<T>(path, {
      method,
      body:
        body === undefined
          ? undefined
          : JSON.stringify(body),
    });

export const post = withBody("POST");
export const put = withBody("PUT");
export const patch = withBody("PATCH");

export const del = (path: string) =>
  api<void>(path, {
    method: "DELETE",
  });

export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const reload = useCallback(() => {
    if (!path) return;

    setLoading(true);

    api<T>(path)
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e: Error) => {
        setError(e.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [path]);

  useEffect(() => {
    reload();
  }, [reload]);

  return {
    data,
    error,
    loading,
    reload,
    setData,
  };
}

export function qs(
  params: Record<string, string | number | undefined | null>
) {
  const p = new URLSearchParams();

  Object.entries(params).forEach(([k, v]) => {
    if (
      v !== undefined &&
      v !== null &&
      v !== ""
    ) {
      p.set(k, String(v));
    }
  });

  const s = p.toString();

  return s ? `?${s}` : "";
}
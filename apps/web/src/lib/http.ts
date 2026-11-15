import { useCallback, useEffect, useState } from "react";

export const API = import.meta.env.VITE_API_URL ?? "/api";
export const getToken = () => localStorage.getItem("gigbid_token") ?? "";
export const setToken = (t: string) => (t ? localStorage.setItem("gigbid_token", t) : localStorage.removeItem("gigbid_token"));

export async function api<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const res = await fetch(API + path, {
    method,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${getToken()}` },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 401 && !path.startsWith("/auth")) {
    setToken("");
    window.location.href = "/login";
  }
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? `Request failed (${res.status})`);
  return res.json();
}

/** Load a resource; `reload` refetches, `every` polls (used while an agent run is in progress). */
export function useApi<T>(path: string | null, every = 0) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const reload = useCallback(() => {
    if (!path) return;
    api<T>(path).then((d) => { setData(d); setError(""); }).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, [path]);
  useEffect(() => {
    reload();
    if (!every) return;
    const id = setInterval(reload, every);
    return () => clearInterval(id);
  }, [reload, every]);
  return { data, error, loading, reload };
}

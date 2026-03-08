/**
 * HTTP client wrapper for FastAPI backend.
 * Handles response envelope unwrapping and typed errors.
 */

import type { ApiResponse, ApiError } from '../types/api';

import { BASE_URL } from '../config';

export class ApiClientError extends Error {
  code: string;
  details: Record<string, unknown>;
  httpStatus: number;

  constructor(error: ApiError, httpStatus: number) {
    super(error.message);
    this.name = 'ApiClientError';
    this.code = error.code;
    this.details = error.details;
    this.httpStatus = httpStatus;
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const url = `${BASE_URL}${path}`;

  const headers: Record<string, string> = {};
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  const json: ApiResponse<T> = await res.json();

  if (!json.success || json.error) {
    throw new ApiClientError(
      json.error ?? { code: 'UNKNOWN', message: 'Unknown error', details: {} },
      res.status,
    );
  }

  return json.data as T;
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
  del: <T>(path: string) => request<T>('DELETE', path),
};

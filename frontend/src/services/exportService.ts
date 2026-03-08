import { BASE_URL } from '../config';

/** Download a file from an export endpoint via POST. */
export async function downloadExport(
  url: string,
  filename: string,
  body?: Record<string, unknown>,
): Promise<void> {
  const response = await fetch(`${BASE_URL}${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) throw new Error(`Export failed: ${response.status}`);

  const blob = await response.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}

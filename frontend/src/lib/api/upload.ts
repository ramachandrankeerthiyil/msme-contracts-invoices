import {
  ApiError,
  GENERIC_ERROR_MESSAGE,
  logFailure,
  SERVICE_UNAVAILABLE_MESSAGE,
  toApiError,
} from './client'

interface UploadOptions {
  fieldName?: string
  /** Called with 0…1 as the file is sent. */
  onProgress?: (fraction: number) => void
}

/**
 * Multipart file upload with progress. Uses XMLHttpRequest because fetch cannot report upload
 * progress. Errors become ApiError exactly like apiFetch.
 */
export function apiUpload<T>(path: string, file: File, options: UploadOptions = {}): Promise<T> {
  const url = path.startsWith('/api/') ? path : `/api${path}`
  const { fieldName = 'file', onProgress } = options

  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', url)
    xhr.setRequestHeader('Accept', 'application/json')

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(event.loaded / event.total)
    }

    xhr.onload = async () => {
      const requestId = xhr.getResponseHeader('X-Request-ID') ?? undefined
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as T)
        } catch {
          reject(new ApiError(xhr.status, 'HTTP_ERROR', GENERIC_ERROR_MESSAGE, requestId))
        }
        return
      }
      const headers = new Headers(requestId ? { 'X-Request-ID': requestId } : {})
      const error = await toApiError(
        new Response(xhr.responseText || null, { status: xhr.status, headers }),
      )
      logFailure('POST', url, error)
      reject(error)
    }

    xhr.onerror = () => {
      const error = new ApiError(0, 'SERVICE_UNAVAILABLE', SERVICE_UNAVAILABLE_MESSAGE)
      logFailure('POST', url, error)
      reject(error)
    }

    const form = new FormData()
    form.append(fieldName, file)
    xhr.send(form)
  })
}

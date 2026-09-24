import type { UploadListItem } from '../api'

function count(n: number, singular: string, plural = `${singular}s`): string {
  return `${n.toLocaleString('en-IN')} ${n === 1 ? singular : plural}`
}

/** "120 rows read · 100 new · 15 updated · 2 replaced by a later row · 3 need fixing" (AC9). */
export function uploadSummaryText(upload: UploadListItem): string {
  const parts = [`${count(upload.rows_total, 'row')} read`]
  if (upload.rows_created) parts.push(`${upload.rows_created.toLocaleString('en-IN')} new`)
  if (upload.rows_updated) parts.push(`${upload.rows_updated.toLocaleString('en-IN')} updated`)
  if (upload.rows_overwritten) {
    parts.push(`${upload.rows_overwritten.toLocaleString('en-IN')} replaced by a later row`)
  }
  if (upload.rows_rejected) {
    parts.push(`${upload.rows_rejected.toLocaleString('en-IN')} ${upload.rows_rejected === 1 ? 'needs' : 'need'} fixing`)
  }
  return parts.join(' · ')
}

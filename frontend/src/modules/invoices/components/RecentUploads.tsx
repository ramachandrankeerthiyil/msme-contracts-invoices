import { useQuery } from '@tanstack/react-query'

import { QueryBoundary } from '@/components/common/QueryBoundary'
import { StatusBadge } from '@/components/common/StatusBadge'
import { Table, TBody, Td, Th, THead, Tr } from '@/components/ui/table'
import { formatDateTime } from '@/lib/format'

import { invoiceKeys, listUploads } from '../api'

/** The last 5 invoice uploads (INV-001 AC8). */
export function RecentUploads() {
  const query = useQuery({ queryKey: invoiceKeys.uploads(), queryFn: () => listUploads(5) })

  return (
    <section aria-labelledby="recent-uploads-heading" className="flex flex-col gap-4">
      <h2 id="recent-uploads-heading" className="text-h2">
        Recent uploads
      </h2>
      <QueryBoundary query={query}>
        {(page) =>
          page.items.length === 0 ? (
            <p className="text-text-muted">No uploads yet. Your uploads will be listed here.</p>
          ) : (
            <Table caption="Recent invoice uploads">
              <THead>
                <Tr>
                  <Th>Uploaded</Th>
                  <Th>File</Th>
                  <Th numeric>Rows read</Th>
                  <Th numeric>New</Th>
                  <Th numeric>Updated</Th>
                  <Th numeric>Need fixing</Th>
                  <Th>Result</Th>
                </Tr>
              </THead>
              <TBody>
                {page.items.map((upload) => (
                  <Tr key={upload.id}>
                    <Td className="whitespace-nowrap">{formatDateTime(upload.uploaded_at)}</Td>
                    <Td className="max-w-64 truncate" title={upload.file_name}>
                      {upload.file_name}
                    </Td>
                    <Td numeric>{upload.rows_total}</Td>
                    <Td numeric>{upload.rows_created}</Td>
                    <Td numeric>{upload.rows_updated}</Td>
                    <Td numeric>{upload.rows_rejected}</Td>
                    <Td>
                      {upload.status === 'completed' ? (
                        <StatusBadge variant="success" label="Saved" />
                      ) : (
                        <StatusBadge variant="warning" label="Nothing saved" />
                      )}
                    </Td>
                  </Tr>
                ))}
              </TBody>
            </Table>
          )
        }
      </QueryBoundary>
    </section>
  )
}

import { useQuery } from '@tanstack/react-query'
import { FileText, Upload } from 'lucide-react'

import { EmptyState } from '@/components/common/EmptyState'
import { QueryBoundary } from '@/components/common/QueryBoundary'
import { ButtonLink } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

import { contractKeys, getDashboard } from '../api'
import { ContractKpis } from './ContractKpis'

/** Contract headline numbers on Home (PLT-001 AC5); loads and fails on its own (AC10). */
export function ContractsOverview() {
  const query = useQuery({ queryKey: contractKeys.dashboard(), queryFn: getDashboard })
  return (
    <QueryBoundary query={query} loading={<Skeleton className="h-64 w-full" />}>
      {(data) =>
        data.has_data ? (
          <ContractKpis data={data} compact />
        ) : (
          <EmptyState
            icon={FileText}
            title="No contracts yet"
            description="Upload a contract and we will pick out the parties, key dates, terms and risks for you."
            action={
              <ButtonLink to="/contracts/upload">
                <Upload aria-hidden />
                Upload contract
              </ButtonLink>
            }
          />
        )
      }
    </QueryBoundary>
  )
}

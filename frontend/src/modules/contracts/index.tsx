import { FileText, LayoutDashboard, Upload } from 'lucide-react'

import type { Crumb, ModuleDefinition, PageAction } from '@/app/types'

import { ContractDashboardPage } from './pages/ContractDashboardPage'
import { ContractDetailPage } from './pages/ContractDetailPage'
import { ContractsPage } from './pages/ContractsPage'
import { UploadContractPage } from './pages/UploadContractPage'

const parents: Crumb[] = [{ label: 'Contracts', to: '/contracts/dashboard' }]
const uploadAction: PageAction = { label: 'Upload contract', to: '/contracts/upload', icon: Upload }

export const contractsModule: ModuleDefinition = {
  id: 'contracts',
  label: 'Contracts',
  nav: [
    { label: 'Dashboard', to: '/contracts/dashboard', icon: LayoutDashboard },
    { label: 'All contracts', to: '/contracts', icon: FileText },
    { label: 'Upload contract', to: '/contracts/upload', icon: Upload },
  ],
  routes: [
    {
      path: 'contracts',
      children: [
        {
          index: true,
          element: <ContractsPage />,
          handle: { title: 'All contracts', crumb: 'All contracts', parents, action: uploadAction },
        },
        {
          path: 'dashboard',
          element: <ContractDashboardPage />,
          handle: { title: 'Contract dashboard', crumb: 'Dashboard', parents, action: uploadAction },
        },
        {
          path: 'upload',
          element: <UploadContractPage />,
          handle: { title: 'Upload contract', crumb: 'Upload', parents },
        },
        {
          path: ':contractId',
          element: <ContractDetailPage />,
          handle: {
            title: 'Contract details',
            crumb: 'Contract details',
            parents: [...parents, { label: 'All contracts', to: '/contracts' }],
          },
        },
      ],
    },
  ],
}

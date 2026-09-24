import { FileText, LayoutDashboard, Upload } from 'lucide-react'

import type { Crumb, ModuleDefinition, PageAction } from '@/app/types'
import { ComingSoonPage } from '@/pages/ComingSoonPage'

const parents: Crumb[] = [{ label: 'Contracts', to: '/contracts/dashboard' }]
const uploadAction: PageAction = { label: 'Upload contract', to: '/contracts/upload', icon: Upload }

// Pages are ComingSoon placeholders until CON-001 … CON-003 deliver them.
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
          element: <ComingSoonPage />,
          handle: { title: 'All contracts', crumb: 'All contracts', parents, action: uploadAction },
        },
        {
          path: 'dashboard',
          element: <ComingSoonPage />,
          handle: { title: 'Contract dashboard', crumb: 'Dashboard', parents, action: uploadAction },
        },
        {
          path: 'upload',
          element: <ComingSoonPage />,
          handle: { title: 'Upload contract', crumb: 'Upload', parents },
        },
        {
          path: ':contractId',
          element: <ComingSoonPage />,
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

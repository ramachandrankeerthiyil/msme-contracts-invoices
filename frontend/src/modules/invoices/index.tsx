import { LayoutDashboard, ReceiptIndianRupee, Upload } from 'lucide-react'

import type { Crumb, ModuleDefinition, PageAction } from '@/app/types'
import { ComingSoonPage } from '@/pages/ComingSoonPage'

const parents: Crumb[] = [{ label: 'Invoices', to: '/invoices/dashboard' }]
const uploadAction: PageAction = { label: 'Upload invoices', to: '/invoices/upload', icon: Upload }

// Pages are ComingSoon placeholders until INV-001 … INV-003 deliver them.
export const invoicesModule: ModuleDefinition = {
  id: 'invoices',
  label: 'Invoices',
  nav: [
    { label: 'Dashboard', to: '/invoices/dashboard', icon: LayoutDashboard },
    { label: 'All invoices', to: '/invoices', icon: ReceiptIndianRupee },
    { label: 'Upload invoices', to: '/invoices/upload', icon: Upload },
  ],
  routes: [
    {
      path: 'invoices',
      children: [
        {
          index: true,
          element: <ComingSoonPage />,
          handle: { title: 'All invoices', crumb: 'All invoices', parents, action: uploadAction },
        },
        {
          path: 'dashboard',
          element: <ComingSoonPage />,
          handle: { title: 'Invoice dashboard', crumb: 'Dashboard', parents, action: uploadAction },
        },
        {
          path: 'upload',
          element: <ComingSoonPage />,
          handle: { title: 'Upload invoices', crumb: 'Upload', parents },
        },
      ],
    },
  ],
}

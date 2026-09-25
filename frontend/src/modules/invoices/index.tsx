import { LayoutDashboard, ReceiptIndianRupee, Upload } from 'lucide-react'

import type { Crumb, ModuleDefinition, PageAction } from '@/app/types'

import { InvoiceDashboardPage } from './pages/InvoiceDashboardPage'
import { InvoicesPage } from './pages/InvoicesPage'
import { UploadInvoicesPage } from './pages/UploadInvoicesPage'

const parents: Crumb[] = [{ label: 'Invoices', to: '/invoices/dashboard' }]
const uploadAction: PageAction = { label: 'Upload invoices', to: '/invoices/upload', icon: Upload }

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
          element: <InvoicesPage />,
          handle: { title: 'All invoices', crumb: 'All invoices', parents, action: uploadAction },
        },
        {
          path: 'dashboard',
          element: <InvoiceDashboardPage />,
          handle: { title: 'Invoice dashboard', crumb: 'Dashboard', parents, action: uploadAction },
        },
        {
          path: 'upload',
          element: <UploadInvoicesPage />,
          handle: { title: 'Upload invoices', crumb: 'Upload', parents },
        },
      ],
    },
  ],
}

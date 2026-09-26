import { Sparkles } from 'lucide-react'

import type { ModuleDefinition } from '@/app/types'

import { AssistantPage } from './pages/AssistantPage'

export const assistantModule: ModuleDefinition = {
  id: 'assistant',
  label: 'Assistant',
  nav: [{ label: 'Talk to Me', to: '/assistant', icon: Sparkles }],
  routes: [
    {
      path: 'assistant',
      element: <AssistantPage />,
      handle: {
        title: 'Talk to Me',
        crumb: 'Talk to Me',
        parents: [{ label: 'Assistant' }],
      },
    },
  ],
}

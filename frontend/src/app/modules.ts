import { assistantModule } from '@/modules/assistant'
import { contractsModule } from '@/modules/contracts'
import { invoicesModule } from '@/modules/invoices'

import type { ModuleDefinition } from './types'

// Module registry: adding a business module = adding one entry here (PLT-001 design).
export const modules: ModuleDefinition[] = [contractsModule, invoicesModule, assistantModule]

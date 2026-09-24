import { Menu, X } from 'lucide-react'
import { useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Sheet, SheetClose, SheetContent, SheetTrigger } from '@/components/ui/sheet'

import { NavLinks } from './NavLinks'

/**
 * Below 1024px the sidebar is replaced by a labelled "Menu" button that opens the same
 * navigation in a side sheet (PLT-001 AC7). Escape closes it and focus returns to the button;
 * after choosing a page, focus goes to the new page's heading instead (AC8).
 */
export function MobileNav() {
  const [open, setOpen] = useState(false)
  const navigated = useRef(false)

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="secondary" className="px-4 lg:hidden">
          <Menu aria-hidden />
          Menu
        </Button>
      </SheetTrigger>
      <SheetContent
        title="Main menu"
        onCloseAutoFocus={(event) => {
          if (navigated.current) {
            event.preventDefault()
            navigated.current = false
          }
        }}
      >
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <span className="text-h3">Menu</span>
          <SheetClose asChild>
            <Button variant="secondary" className="px-4">
              <X aria-hidden />
              Close
            </Button>
          </SheetClose>
        </div>
        <NavLinks
          label="Main menu"
          onNavigate={() => {
            navigated.current = true
            setOpen(false)
          }}
        />
      </SheetContent>
    </Sheet>
  )
}

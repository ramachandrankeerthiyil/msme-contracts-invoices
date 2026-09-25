import { Search, X } from 'lucide-react'
import { useEffect, useState } from 'react'

const SEARCH_DELAY_MS = 300

interface SearchFieldProps {
  id: string
  label: string
  placeholder?: string
  /** The applied search (from the URL). */
  value: string
  onSearch: (value: string) => void
}

/**
 * Labelled search box: applies the search once typing pauses, or at once on Enter, and follows the
 * URL when it changes elsewhere (Back button, Clear filters).
 */
export function SearchField({ id, label, placeholder, value, onSearch }: SearchFieldProps) {
  const [text, setText] = useState(value)

  useEffect(() => setText(value), [value])

  useEffect(() => {
    if (text.trim() === value) return
    const timer = setTimeout(() => onSearch(text.trim()), SEARCH_DELAY_MS)
    return () => clearTimeout(timer)
  }, [text, value, onSearch])

  return (
    <form
      role="search"
      className="flex w-full max-w-xl flex-col gap-2"
      onSubmit={(event) => {
        event.preventDefault()
        onSearch(text.trim())
      }}
    >
      <label htmlFor={id} className="font-semibold">
        {label}
      </label>
      <div className="relative">
        <Search
          aria-hidden
          className="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2 text-text-muted"
        />
        <input
          id={id}
          type="text"
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={placeholder}
          autoComplete="off"
          className="h-12 w-full rounded-md border border-border bg-bg pr-14 pl-12 text-body placeholder:text-text-muted"
        />
        {text && (
          <button
            type="button"
            aria-label="Clear search"
            onClick={() => {
              setText('')
              onSearch('')
            }}
            className="absolute top-1/2 right-0.5 grid size-11 -translate-y-1/2 place-items-center rounded-md text-text-muted hover:bg-surface-strong"
          >
            <X aria-hidden className="size-5" />
          </button>
        )}
      </div>
    </form>
  )
}

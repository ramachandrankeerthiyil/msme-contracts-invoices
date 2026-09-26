import Markdown, { type Components } from 'react-markdown'
import { Link } from 'react-router'
import remarkGfm from 'remark-gfm'

// Answers are Markdown (AST-001 AC7, AC9). Raw HTML is never rendered (react-markdown's
// default), and only links to records inside the app become links; anything else is shown
// as plain text, so neither the AI nor contract text can send users elsewhere.

const IN_APP_LINK = /^\/(?:contracts|invoices)(?:[/?#]|$)/

export function isInAppLink(href: string | undefined): href is string {
  return !!href && IN_APP_LINK.test(href)
}

const components: Components = {
  a({ href, children }) {
    if (!isInAppLink(href)) return <span>{children}</span>
    return (
      <Link to={href} className="link">
        {children}
      </Link>
    )
  },
  p: (props) => <p className="my-3 first:mt-0 last:mb-0" {...strip(props)} />,
  ul: (props) => <ul className="my-3 list-disc space-y-1 pl-7" {...strip(props)} />,
  ol: (props) => <ol className="my-3 list-decimal space-y-1 pl-7" {...strip(props)} />,
  h1: (props) => <p className="mt-4 mb-2 text-h3" {...strip(props)} />,
  h2: (props) => <p className="mt-4 mb-2 text-h3" {...strip(props)} />,
  h3: (props) => <p className="mt-4 mb-2 font-semibold" {...strip(props)} />,
  strong: (props) => <strong className="font-semibold" {...strip(props)} />,
  code: (props) => <code className="rounded-md bg-surface px-1 font-mono text-small" {...strip(props)} />,
  pre: (props) => <pre className="my-3 overflow-x-auto rounded-md bg-surface p-4" {...strip(props)} />,
  blockquote: (props) => (
    <blockquote className="my-3 border-l-4 border-border pl-4 text-text-muted" {...strip(props)} />
  ),
  table: (props) => (
    <div className="my-4 overflow-x-auto rounded-lg border border-border">
      <table className="w-full border-collapse text-left text-small" {...strip(props)} />
    </div>
  ),
  thead: (props) => <thead className="bg-surface" {...strip(props)} />,
  tbody: (props) => <tbody className="[&>tr:nth-child(even)]:bg-surface" {...strip(props)} />,
  tr: (props) => <tr className="border-b border-border last:border-b-0" {...strip(props)} />,
  th: (props) => (
    <th scope="col" className="h-12 border-b border-border px-4 font-semibold whitespace-nowrap" {...strip(props)} />
  ),
  td: (props) => <td className="px-4 py-2 align-top" {...strip(props)} />,
  img: ({ alt }) => <span>{alt}</span>,
}

/** Drops react-markdown's `node` prop so it isn't passed to the DOM. */
function strip<T extends { node?: unknown }>({ node: _node, ...rest }: T): Omit<T, 'node'> {
  return rest
}

export function AnswerMarkdown({ text }: { text: string }) {
  return (
    <div className="max-w-none break-words">
      <Markdown remarkPlugins={[remarkGfm]} components={components}>
        {text}
      </Markdown>
    </div>
  )
}

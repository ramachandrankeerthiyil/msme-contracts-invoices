import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { FileDropzone } from './FileDropzone'

function setup() {
  const onFile = vi.fn()
  render(
    <FileDropzone
      accept={['.xlsx']}
      acceptLabel="an Excel file (.xlsx)"
      maxBytes={1024}
      title="Drag your Excel file here"
      helpText="Excel (.xlsx), up to 10 MB."
      onFile={onFile}
    />,
  )
  return { onFile, input: screen.getByTestId('file-input') as HTMLInputElement }
}

const xlsx = (name = 'invoices.xlsx', size = 10) => new File(['x'.repeat(size)], name)

describe('INV_001_AC1 FileDropzone', () => {
  it('offers a Choose file button and states formats and size', () => {
    setup()

    expect(screen.getByRole('button', { name: 'Choose file' })).toBeInTheDocument()
    expect(screen.getByText('Excel (.xlsx), up to 10 MB.')).toBeInTheDocument()
  })

  it('accepts an .xlsx file (any case)', async () => {
    const { onFile, input } = setup()

    await userEvent.upload(input, xlsx('Invoices.XLSX'))

    expect(onFile).toHaveBeenCalledOnce()
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('rejects other file types with a plain-language message', async () => {
    const { onFile, input } = setup()

    await userEvent.upload(input, new File(['a,b'], 'invoices.csv'), { applyAccept: false })

    expect(onFile).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent(
      "This file type isn't supported. Please choose an Excel file (.xlsx).",
    )
  })

  it('rejects files over the size limit', async () => {
    const { onFile, input } = setup()

    await userEvent.upload(input, xlsx('big.xlsx', 2048))

    expect(onFile).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent('This file is larger than 1 KB.')
  })

  it('accepts a dropped file', () => {
    const { onFile } = setup()
    const zone = screen.getByText('Drag your Excel file here').parentElement as HTMLElement

    fireEvent.drop(zone, { dataTransfer: { files: [xlsx()] } })

    expect(onFile).toHaveBeenCalledOnce()
  })
})

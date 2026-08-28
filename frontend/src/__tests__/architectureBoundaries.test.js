import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const architectureFiles = [
  'src/App.jsx',
  'src/routes/router.jsx',
  'src/routes/protectedRoutes.jsx',
  'src/components/layout/AppShell.jsx',
  'src/components/layout/SidebarContent.jsx',
  'src/components/prompts/PromptManager.jsx',
  'src/components/prompts/PromptEditor.jsx',
  'src/components/prompts/PromptTestPanel.jsx',
  'src/components/prompts/PromptAIDraft.jsx',
  'src/components/prompts/PromptHistory.jsx',
]

describe('Phase 3 architecture boundaries', () => {
  it.each(architectureFiles)('%s remains below 400 lines', (file) => {
    const lineCount = readFileSync(resolve(process.cwd(), file), 'utf8').split(/\r?\n/).length
    expect(lineCount).toBeLessThan(400)
  })
})

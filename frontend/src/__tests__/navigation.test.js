import { describe, expect, it } from 'vitest'

import { getNavigationGroups } from '../navigation'

describe('navigation groups', () => {
  it('keeps administrative navigation out of standard workspaces', () => {
    const groups = getNavigationGroups(false)
    expect(groups.some((group) => group.name === 'Admin')).toBe(false)
    expect(groups.flatMap((group) => group.items).some((item) => item.id === 'inbox')).toBe(true)
  })

  it('adds protected administration destinations for administrators', () => {
    const admin = getNavigationGroups(true).find((group) => group.name === 'Admin')
    expect(admin.items.map((item) => item.id)).toEqual([
      'admin-dashboard',
      'admin-llm',
      'admin-user-access',
      'admin-feature-rules',
    ])
  })
})

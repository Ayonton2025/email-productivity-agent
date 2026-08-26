import { describe, expect, it } from 'vitest'
import { getEmailPreview, parseEmailBody } from '../utils/emailParser'

describe('email previews', () => {
  it('removes URLs from preview text', () => expect(getEmailPreview('Read https://example.com now')).toBe('Read  now'))
  it('preserves empty lines as layout tokens', () => expect(parseEmailBody('First\n\nSecond')[1].type).toBe('empty'))
})

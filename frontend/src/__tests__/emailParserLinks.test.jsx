import { describe, expect, it } from 'vitest'
import { extractLinksFromEmail, parseEmailBody, shortenUrl } from '../utils/emailParser'

describe('email link parsing', () => {
  it('turns bare links into link tokens', () =>
    expect(parseEmailBody('Visit https://example.com/docs')[0].content.some((item) => item.type === 'link')).toBe(true))
  it('deduplicates extracted links', () =>
    expect(extractLinksFromEmail('https://example.com https://example.com')).toEqual(['https://example.com']))
  it('shortens long URLs for display', () =>
    expect(shortenUrl('https://example.com/a/very/long/path', 20).length).toBeLessThanOrEqual(20))
})

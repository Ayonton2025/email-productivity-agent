import { describe, expect, it } from 'vitest';
import { formatEmailDateLocal, getUserTimeZone } from '../utils/timezone';

describe('timezone utilities', () => {
  it('returns a timezone name', () => expect(getUserTimeZone()).toEqual(expect.any(String)));
  it('returns blank output for invalid dates', () =>
    expect(formatEmailDateLocal('not-a-date')).toBe(''));
});

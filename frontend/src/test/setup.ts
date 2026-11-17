/**
 * Vitest + Testing Library bootstrap.
 *
 * Side Effects:
 * - Registers jest-dom matchers for every test file.
 * - Clears localStorage between tests to avoid theme / auth bleed.
 */
import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(() => {
  cleanup();
  localStorage.clear();
});

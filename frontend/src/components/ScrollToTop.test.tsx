import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Link, Route, Routes, useSearchParams } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ScrollToTop } from './ScrollToTop';

function Page() {
  const [params, setParams] = useSearchParams();
  return (
    <>
      <Link to="/b">go b</Link>
      <button type="button" onClick={() => setParams({ draft: '1' })}>
        set draft
      </button>
      <span>{params.get('draft') ?? 'none'}</span>
    </>
  );
}

describe('ScrollToTop', () => {
  let scrollSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    scrollSpy = vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
  });

  afterEach(() => {
    scrollSpy.mockRestore();
  });

  it('scrolls to the top when the path changes', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/a']}>
        <ScrollToTop />
        <Routes>
          <Route path="/a" element={<Page />} />
          <Route path="/b" element={<div>b page</div>} />
        </Routes>
      </MemoryRouter>,
    );
    scrollSpy.mockClear();
    await user.click(screen.getByRole('link', { name: 'go b' }));
    expect(screen.getByText('b page')).toBeInTheDocument();
    expect(scrollSpy).toHaveBeenCalledWith(0, 0);
  });

  it('keeps the position when only the query string changes', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/a']}>
        <ScrollToTop />
        <Routes>
          <Route path="/a" element={<Page />} />
        </Routes>
      </MemoryRouter>,
    );
    scrollSpy.mockClear();
    await user.click(screen.getByRole('button', { name: 'set draft' }));
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(scrollSpy).not.toHaveBeenCalled();
  });
});

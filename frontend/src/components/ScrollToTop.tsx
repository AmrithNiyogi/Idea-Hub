import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

/**
 * Scrolls the window to the top when the route path changes.
 *
 * Keyed on the pathname only, so query-only updates (for example the draft
 * save on /submit that rewrites ?draft=) keep the user's place on the page.
 */
export function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return null;
}

export default ScrollToTop;

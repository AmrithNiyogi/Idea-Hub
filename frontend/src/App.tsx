import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { ScrollToTop } from './components/ScrollToTop';
import { AuthProvider } from './auth/AuthProvider';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { AppShell } from './components/shell/AppShell';
import { ToastProvider } from './components/ToastProvider';
import { LoginPage } from './pages/Login';
import { HomePage } from './pages/Home';
import { ExplorePage } from './pages/Explore';
import { IdeaDetailPage } from './pages/IdeaDetail';
import { SubmitPage } from './pages/Submit';
import { ReviewPage } from './pages/Review';
import { ReviewDetailPage } from './pages/ReviewDetail';
import { MyIdeasPage } from './pages/MyIdeas';
import { collectExtraRoutes } from './routeModules';

export function App() {
  const extraRoutes = collectExtraRoutes();

  return (
    <ToastProvider>
      <AuthProvider>
        <BrowserRouter>
          <ScrollToTop />
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              element={
                <ProtectedRoute>
                  <AppShell />
                </ProtectedRoute>
              }
            >
              <Route path="/" element={<HomePage />} />
              <Route path="/home" element={<Navigate to="/" replace />} />
              <Route path="/explore" element={<ExplorePage />} />
              <Route path="/ideas/:id" element={<IdeaDetailPage />} />
              <Route path="/submit" element={<SubmitPage />} />
              <Route path="/review" element={<ReviewPage />} />
              <Route path="/review/:id" element={<ReviewDetailPage />} />
              <Route path="/my" element={<MyIdeasPage />} />
              {extraRoutes}
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ToastProvider>
  );
}

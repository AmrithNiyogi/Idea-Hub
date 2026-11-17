import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import * as authApi from '../api/auth';
import type { OtpMethod, Role, User } from '../types/auth';

interface AuthContextValue {
  user: User | null;
  isLoggedIn: boolean;
  isAuthLoading: boolean;
  login: (
    email: string,
    password: string,
    otp: string,
    otpMethod?: OtpMethod,
  ) => Promise<User>;
  logout: () => Promise<void>;
  switchRole: (role: Role) => Promise<void>;
  refetchUser: () => Promise<User | null>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);

  const refetchUser = useCallback(async () => {
    try {
      const me = await authApi.getCurrentUser();
      setUser(me);
      return me;
    } catch {
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setIsAuthLoading(true);
      try {
        const me = await authApi.getCurrentUser();
        if (!cancelled) setUser(me);
      } catch {
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setIsAuthLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(
    async (
      email: string,
      password: string,
      otp: string,
      otpMethod?: OtpMethod,
    ) => {
      const res = await authApi.login({
        email,
        password,
        otp,
        otp_method: otpMethod,
      });
      setUser(res.user);
      return res.user;
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
    }
  }, []);

  const switchRole = useCallback(async (role: Role) => {
    const res = await authApi.switchRole(role);
    setUser(res.user);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoggedIn: !!user,
      isAuthLoading,
      login,
      logout,
      switchRole,
      refetchUser,
    }),
    [user, isAuthLoading, login, logout, switchRole, refetchUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

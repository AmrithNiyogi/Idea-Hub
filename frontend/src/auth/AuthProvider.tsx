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
import type {
  OtpMethod,
  Role,
  RoleSelectionPending,
  User,
} from '../types/auth';

export type LoginOutcome =
  | { status: 'authenticated'; user: User }
  | { status: 'role_selection'; pending: RoleSelectionPending };

interface AuthContextValue {
  user: User | null;
  isLoggedIn: boolean;
  isAuthLoading: boolean;
  login: (
    email: string,
    password: string,
    otp: string,
    otpMethod?: OtpMethod,
  ) => Promise<LoginOutcome>;
  completeLogin: (loginTicket: string, role: Role) => Promise<User>;
  logout: () => Promise<void>;
  switchRole: (role: Role) => Promise<void>;
  refetchUser: () => Promise<User | null>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function pendingFromLogin(
  ticket: string,
  roles: Role[],
  primary: Role,
  name: string,
): RoleSelectionPending {
  return {
    login_ticket: ticket,
    roles,
    primary_role: primary,
    name,
  };
}

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
    ): Promise<LoginOutcome> => {
      const res = await authApi.login({
        email,
        password,
        otp,
        otp_method: otpMethod,
      });
      if (res.requires_role_selection && res.login_ticket) {
        const roles = (res.roles ?? []) as Role[];
        const primary = (res.primary_role ?? roles[0] ?? 'contributor') as Role;
        return {
          status: 'role_selection',
          pending: pendingFromLogin(
            res.login_ticket,
            roles,
            primary,
            res.name ?? email,
          ),
        };
      }
      if (!res.user) {
        throw new Error('Login did not return a user session');
      }
      setUser(res.user);
      return { status: 'authenticated', user: res.user };
    },
    [],
  );

  const completeLogin = useCallback(
    async (loginTicket: string, role: Role) => {
      const res = await authApi.completeLogin({
        login_ticket: loginTicket,
        role,
      });
      if (!res.user) {
        throw new Error('Could not complete login');
      }
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
      completeLogin,
      logout,
      switchRole,
      refetchUser,
    }),
    [
      user,
      isAuthLoading,
      login,
      completeLogin,
      logout,
      switchRole,
      refetchUser,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

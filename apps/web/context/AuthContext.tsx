"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

import {
  httpClient,
  ResponseEnvelope,
  setAccessToken,
  setOnUnauthorized,
} from "../lib/api";

export interface User {
  id: string;
  email: string;
  fullName: string;
  role: string;
  tenantId: string;
  avatarUrl?: string | null;
}

export interface LoginCredentials {
  email: string;
  password: string;
  tenantId: string;
}

export interface LoginData {
  accessToken: string;
  tokenType: string;
  expiresIn: number;
  user: User;
}

export interface RefreshTokenData {
  accessToken: string;
  tokenType: string;
  expiresIn: number;
}

export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<User>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;

    setOnUnauthorized(() => {
      if (isMounted) {
        setUser(null);
        setAccessToken(null);
      }
    });

    async function restoreSession(): Promise<void> {
      try {
        const refreshResponse = await httpClient.post<ResponseEnvelope<RefreshTokenData>>(
          "/api/v1/auth/refresh",
          {},
          { skipAuth: true }
        );

        if (refreshResponse && refreshResponse.data && refreshResponse.data.accessToken) {
          setAccessToken(refreshResponse.data.accessToken);

          const meResponse = await httpClient.get<ResponseEnvelope<User>>("/api/v1/auth/me");
          if (isMounted && meResponse && meResponse.data) {
            setUser(meResponse.data);
          }
        }
      } catch {
        if (isMounted) {
          setAccessToken(null);
          setUser(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    restoreSession();

    return () => {
      isMounted = false;
      setOnUnauthorized(null);
    };
  }, []);

  const login = async (credentials: LoginCredentials): Promise<User> => {
    const loginResponse = await httpClient.post<ResponseEnvelope<LoginData>>(
      "/api/v1/auth/login",
      credentials,
      { skipAuth: true }
    );

    const loginData = loginResponse.data;
    setAccessToken(loginData.accessToken);
    setUser(loginData.user);
    return loginData.user;
  };

  const logout = async (): Promise<void> => {
    try {
      await httpClient.post("/api/v1/auth/logout", {}, { skipAuth: true });
    } catch {
      // Ignore network/server errors during logout
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  };

  const refreshSession = async (): Promise<void> => {
    try {
      const refreshResponse = await httpClient.post<ResponseEnvelope<RefreshTokenData>>(
        "/api/v1/auth/refresh",
        {},
        { skipAuth: true }
      );

      if (refreshResponse && refreshResponse.data && refreshResponse.data.accessToken) {
        setAccessToken(refreshResponse.data.accessToken);

        const meResponse = await httpClient.get<ResponseEnvelope<User>>("/api/v1/auth/me");
        setUser(meResponse.data);
      }
    } catch (err) {
      setAccessToken(null);
      setUser(null);
      throw err;
    }
  };

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: Boolean(user),
    login,
    logout,
    refreshSession,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

export function useCurrentUser(): User | null {
  const { user } = useAuth();
  return user;
}

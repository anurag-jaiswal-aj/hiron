import { apiFetch, ResponseEnvelope } from "./api";

export interface UserResponse {
  id: string;
  tenantId: string;
  email: string;
  fullName: string;
  role: string;
  isActive: boolean;
  isEmailVerified: boolean;
  avatarUrl: string | null;
  lastLoginAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export const usersApi = {
  listUsers: (params?: {
    role?: string;
    isActive?: boolean;
    limit?: number;
    offset?: number;
  }) => {
    return apiFetch<ResponseEnvelope<UserResponse[]>>(`/api/v1/users`, {
      params: params as Record<string, string | number | boolean | null | undefined>,
    }).then((res) => res.data);
  },

  getUser: (userId: string) => {
    return apiFetch<ResponseEnvelope<UserResponse>>(`/api/v1/users/${userId}`).then(
      (res) => res.data
    );
  },
};

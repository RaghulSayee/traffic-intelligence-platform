export type UserRole =
  | "admin"
  | "reviewer";

export type AuthUser = {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type LoginResponse = {
  user: AuthUser;
};

export type SessionResponse = {
  user: AuthUser;
};

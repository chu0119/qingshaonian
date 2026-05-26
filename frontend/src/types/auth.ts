export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserInfo;
}

export interface UserInfo {
  id: number;
  school_id: number | null;
  username: string;
  real_name: string;
  role: string;
  teacher_type: string | null;
  gender: string;
  phone: string;
  student_no: string;
  grade_id: number | null;
  class_id: number | null;
  must_change_password: boolean;
}

export type UserRole = 'school_admin' | 'teacher' | 'counselor' | 'student' | 'platform_admin';

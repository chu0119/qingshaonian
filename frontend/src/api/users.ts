import client from './client';
import type { PaginatedData } from '../types/common';

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
  birth_date: string | null;
  grade_id: number | null;
  class_id: number | null;
  status: boolean;
  grade_name: string;
  class_name: string;
  created_at: string | null;
}

export async function getStudents(params?: Record<string, unknown>) {
  const res = await client.get('/users/students', { params });
  return res.data.data as PaginatedData<UserInfo>;
}

export async function createStudent(data: Record<string, unknown>) {
  const res = await client.post('/users/students', data);
  return res.data;
}

export async function updateStudent(id: number, data: Record<string, unknown>) {
  const res = await client.put(`/users/students/${id}`, data);
  return res.data;
}

export async function deleteStudent(id: number) {
  const res = await client.delete(`/users/students/${id}`);
  return res.data;
}

export async function importStudents(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  // 不手动设置 Content-Type，让浏览器自动添加 boundary 参数
  const res = await client.post('/users/students/import', formData);
  return res.data.data as { success_count: number; fail_count: number; errors: string[] };
}

export async function downloadTemplate() {
  const res = await client.get('/users/students/template', { responseType: 'blob' });
  const url = window.URL.createObjectURL(new Blob([res.data]));
  const a = document.createElement('a');
  a.href = url;
  a.download = 'student_import_template.xlsx';
  a.click();
  window.URL.revokeObjectURL(url);
}

export async function getTeachers(params?: Record<string, unknown>) {
  const res = await client.get('/users/teachers', { params });
  return res.data.data as PaginatedData<UserInfo>;
}

export async function createTeacher(data: Record<string, unknown>) {
  const res = await client.post('/users/teachers', data);
  return res.data;
}

export async function updateTeacher(id: number, data: Record<string, unknown>) {
  const res = await client.put(`/users/teachers/${id}`, data);
  return res.data;
}

export async function deleteTeacher(id: number) {
  const res = await client.delete(`/users/teachers/${id}`);
  return res.data;
}

export async function assignTeacherClasses(teacherId: number, classIds: number[]) {
  const res = await client.put(`/users/teachers/${teacherId}/assign-classes`, classIds);
  return res.data;
}

export async function getTeacherAssignedClasses(teacherId: number) {
  const res = await client.get(`/users/teachers/${teacherId}/assigned-classes`);
  return res.data.data as number[];
}

export async function getDictGrades() {
  const res = await client.get('/common/dict/grades');
  return res.data.data as { value: number; label: string }[];
}

export async function getDictTeacherTypes() {
  const res = await client.get('/common/dict/teacher-types');
  return res.data.data as { value: string; label: string }[];
}

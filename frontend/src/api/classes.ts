import client from './client';
import type { PaginatedData } from '../types/common';

export interface ClassInfo {
  id: number;
  school_id: number;
  grade_id: number;
  name: string;
  head_teacher_id: number | null;
  counselor_id: number | null;
  status: boolean;
  grade_name: string;
  head_teacher_name: string;
  counselor_name: string;
  student_count: number;
}

export async function getClasses(params?: Record<string, unknown>) {
  const res = await client.get('/classes', { params });
  return res.data.data as PaginatedData<ClassInfo>;
}

export async function createClass(data: Record<string, unknown>) {
  const res = await client.post('/classes', data);
  return res.data;
}

export async function updateClass(id: number, data: Record<string, unknown>) {
  const res = await client.put(`/classes/${id}`, data);
  return res.data;
}

export async function deleteClass(id: number) {
  const res = await client.delete(`/classes/${id}`);
  return res.data;
}

/**
 * Global data cache store.
 *
 * Caches frequently-used reference data (schools, classes, questionnaires)
 * to avoid redundant API calls across pages. Data is fetched once and
 * reused until the page reloads.
 */
import { create } from 'zustand';
import client from '../api/client';

interface CacheEntry<T> {
  data: T;
  fetchedAt: number;
}

const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

function isFresh<T>(entry: CacheEntry<T> | null | undefined): entry is CacheEntry<T> {
  return !!entry && Date.now() - entry.fetchedAt < CACHE_TTL;
}

interface DataCacheState {
  schools: CacheEntry<{ value: number; label: string }[]> | null;
  classes: CacheEntry<{ value: number; label: string; grade_name?: string }[]> | null;
  questionnaires: CacheEntry<{ value: number; label: string }[]> | null;

  fetchSchools: () => Promise<{ value: number; label: string }[]>;
  fetchClasses: (schoolId?: number) => Promise<{ value: number; label: string; grade_name?: string }[]>;
  fetchQuestionnaires: (schoolId?: number) => Promise<{ value: number; label: string }[]>;
  clearAll: () => void;
}

export const useDataCache = create<DataCacheState>((set, get) => ({
  schools: null,
  classes: null,
  questionnaires: null,

  fetchSchools: async () => {
    const cached = get().schools;
    if (isFresh(cached)) return cached!.data;
    try {
      const r = await client.get('/platform/schools', { params: { page: 1, page_size: 500 } });
      const items = (r.data.data?.items || []).map((s: any) => ({ value: s.id, label: s.name }));
      set({ schools: { data: items, fetchedAt: Date.now() } });
      return items;
    } catch {
      return [];
    }
  },

  fetchClasses: async (schoolId?: number) => {
    const cached = get().classes;
    if (isFresh(cached) && !schoolId) return cached!.data;
    try {
      const params: Record<string, any> = { page: 1, page_size: 500 };
      if (schoolId) params.school_id = schoolId;
      const r = await client.get('/classes', { params });
      const items = (r.data.data?.items || []).map((c: any) => ({
        value: c.id, label: c.name, grade_name: c.grade_name,
      }));
      if (!schoolId) set({ classes: { data: items, fetchedAt: Date.now() } });
      return items;
    } catch {
      return [];
    }
  },

  fetchQuestionnaires: async (schoolId?: number) => {
    const cached = get().questionnaires;
    if (isFresh(cached) && !schoolId) return cached!.data;
    try {
      const params: Record<string, any> = { page: 1, page_size: 200 };
      if (schoolId) params.school_id = schoolId;
      const r = await client.get('/questionnaires', { params });
      const items = (r.data.data?.items || []).map((q: any) => ({ value: q.id, label: q.title || q.name }));
      if (!schoolId) set({ questionnaires: { data: items, fetchedAt: Date.now() } });
      return items;
    } catch {
      return [];
    }
  },

  clearAll: () => set({ schools: null, classes: null, questionnaires: null }),
}));

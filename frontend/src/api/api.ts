/**
 * API prefix resolver for impersonation mode.
 *
 * When a platform_admin enters a school context, school-level pages
 * should call school-level APIs (no /platform prefix). Platform pages
 * should continue using /platform prefix.
 *
 * Usage:
 *   import { apiPrefix } from '../api/api';
 *   client.get(`${apiPrefix()}/risks`);
 */
import { useAuthStore } from '../stores/authStore';

export function isImpersonating(): boolean {
  return !!localStorage.getItem('platform_token');
}

export function apiPrefix(): string {
  const path = window.location.pathname;
  if (path.startsWith('/platform/')) return '/platform';
  return '';
}

import { client } from '../api-client/client.gen';
import { toast } from 'sonner';
import { getAuthToken } from './auth-token';
import { API_BASE } from './constants';

let initialized = false;

export function setupApi() {
  if (initialized) return;
  initialized = true;

  client.setConfig({
    baseUrl: API_BASE,
  });

  client.interceptors.request.use(async (request) => {
    const token = getAuthToken();
    if (token) {
      request.headers.set('Authorization', `Bearer ${token}`);
    }
    return request;
  });

  client.interceptors.response.use(async (response) => {
    if (response.status === 401) {
      toast.error('Your session expired. Please sign in again.');
      const { supabase } = await import('./supabase');
      await supabase?.auth.signOut();
    }
    return response;
  });

  client.interceptors.error.use(async (error) => {
    if (error instanceof Error) {
      error.message = error.message.replace(/<[^>]*>/g, '').trim();
    }
    return error;
  });
}

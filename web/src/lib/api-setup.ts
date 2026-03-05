import { client } from '../api-client/client.gen';
import { getAuthToken } from './auth-token';
import { API_BASE } from './constants';

export function setupApi() {
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
}

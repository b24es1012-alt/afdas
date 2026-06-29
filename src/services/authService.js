import api from '../config/axios';
import { ENDPOINTS } from '../utils/constants';

export const authService = {
  async login(email, password) {
    const res = await api.post(ENDPOINTS.LOGIN, { email, password });
    return res.data; // { access_token, refresh_token, user }
  },

  async register(email, password, fullName) {
    const res = await api.post(ENDPOINTS.REGISTER, {
      email,
      password,
      full_name: fullName,
    });
    return res.data;
  },

  async refresh(refreshToken) {
    const res = await api.post(ENDPOINTS.REFRESH, {
      refresh_token: refreshToken,
    });
    return res.data;
  },
};

export default authService;

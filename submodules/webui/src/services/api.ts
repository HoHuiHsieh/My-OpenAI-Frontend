/**
 * API service for making HTTP requests
 * This module sets up an axios instance with a base URL and includes an interceptor
 * to automatically attach the authentication token from local storage to each request.
 * It is used throughout the application to interact with the backend API.
 */

import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: API_BASE_URL,
});

// Add a request interceptor to include the authentication token
// api.interceptors.request.use(
//   (config) => {
//     try {
//       const access_token = config.headers['Authorization'];
//       if (access_token) {
//         config.headers['Authorization'] = `Bearer ${access_token}`;
//       }
//     } catch (e) {
//       console.error('Failed to parse auth user data', e);
//     }
//     return config;
//   },
//   (error) => Promise.reject(error)
// );
api.interceptors.response.use(
  (response) => response.data,
  (error) => Promise.reject(error)
);

export default api;

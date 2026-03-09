/**
 * AssetLens API Client
 * Axios-based HTTP client with environment-based configuration
 */

import axios from 'axios';

// API Base URL Configuration
// In production: empty string — all /api/... paths are relative to the same origin (nginx proxies)
// In development: set REACT_APP_API_URL=http://localhost:8000 in .env.local
const API_BASE_URL = process.env.REACT_APP_API_URL || '';

console.log('API Base URL:', API_BASE_URL);

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 second timeout
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - Add auth tokens if needed
apiClient.interceptors.request.use(
  (config) => {
    // Add authentication token if available
    const token = localStorage.getItem('assetlens_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Log request in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    }

    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor - Handle errors globally
apiClient.interceptors.response.use(
  (response) => {
    // Log response in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`API Response: ${response.status} ${response.config.url}`);
    }
    return response;
  },
  (error) => {
    // Handle specific error cases
    if (error.response) {
      // Server responded with error status
      const status = error.response.status;
      const message = error.response.data?.detail || error.response.data?.error || 'An error occurred';

      switch (status) {
        case 401:
          // Unauthorized - clear token and redirect to login
          console.error('Unauthorized access - clearing token');
          localStorage.removeItem('assetlens_token');
          // Optionally redirect to login page
          // window.location.href = '/login';
          break;

        case 403:
          // Forbidden
          console.error('Access forbidden:', message);
          break;

        case 404:
          // Not found
          console.error('Resource not found:', error.config.url);
          break;

        case 500:
        case 502:
        case 503:
        case 504:
          // Server errors
          console.error('Server error:', message);
          break;

        default:
          console.error(`API Error (${status}):`, message);
      }

      // Return formatted error
      return Promise.reject({
        status,
        message,
        data: error.response.data
      });
    } else if (error.request) {
      // Request made but no response received
      console.error('No response from server:', error.message);
      return Promise.reject({
        status: 0,
        message: 'No response from server. Please check your connection.',
        data: null
      });
    } else {
      // Error in request configuration
      console.error('Request configuration error:', error.message);
      return Promise.reject({
        status: -1,
        message: error.message,
        data: null
      });
    }
  }
);

// API Methods

/**
 * Health check endpoint
 */
export const checkHealth = async () => {
  const response = await apiClient.get('/health');
  return response.data;
};

/**
 * Get API status
 */
export const getApiStatus = async () => {
  const response = await apiClient.get('/health');
  return response.data;
};

/**
 * Properties API
 */
export const propertiesApi = {
  // Get all properties with filters
  getAll: async (filters = {}) => {
    const response = await apiClient.get('/api/properties', { params: filters });
    return response.data;
  },

  // Get single property by ID
  getById: async (id) => {
    const response = await apiClient.get(`/api/properties/${id}`);
    return response.data;
  },

  // Get property sales history
  getSalesHistory: async (id) => {
    const response = await apiClient.get(`/api/properties/${id}/sales-history`);
    return response.data;
  },

  // Mark property as reviewed
  markReviewed: async (id) => {
    const response = await apiClient.post(`/api/properties/${id}/review`);
    return response.data;
  }
};

/**
 * Areas API
 */
export const areasApi = {
  // Get area statistics
  getStats: async (postcode) => {
    const response = await apiClient.get(`/api/areas/${postcode}/stats`);
    return response.data;
  },

  // Get area trends
  getTrends: async (postcode) => {
    const response = await apiClient.get(`/api/areas/${postcode}/trends`);
    return response.data;
  }
};

/**
 * Dashboard API
 */
export const dashboardApi = {
  // Get dashboard summary stats
  getStats: async () => {
    const response = await apiClient.get('/api/dashboard/stats');
    return response.data;
  },
};

/**
 * Scrapers API
 */
export const scrapersApi = {
  getAll: async () => {
    const response = await apiClient.get('/api/scrapers');
    return response.data;
  },
  add: async (payload) => {
    const response = await apiClient.post('/api/scrapers', payload);
    return response.data;
  },
  delete: async (id) => {
    const response = await apiClient.delete(`/api/scrapers/${id}`);
    return response.data;
  },
  update: async (id, payload) => {
    const response = await apiClient.patch(`/api/scrapers/${id}`, payload);
    return response.data;
  },
  toggle: async (id) => {
    const response = await apiClient.patch(`/api/scrapers/${id}/toggle`);
    return response.data;
  },
  run: async (id) => {
    const response = await apiClient.post(`/api/scrapers/${id}/run`);
    return response.data;
  },
  investigate: async (id) => {
    const response = await apiClient.post(`/api/scrapers/${id}/investigate`);
    return response.data;
  },
  hint: async (id, payload) => {
    const response = await apiClient.post(`/api/scrapers/${id}/hint`, payload);
    return response.data;
  },
  getLibrary: async () => {
    const response = await apiClient.get('/api/scrapers/library');
    return response.data;
  },
  getLogs: async (id, runId) => {
    const url = runId ? `/api/scrapers/${id}/logs?run_id=${runId}` : `/api/scrapers/${id}/logs`;
    const response = await apiClient.get(url);
    return response.data;
  },
};

// Export configured axios instance for custom requests
export default apiClient;

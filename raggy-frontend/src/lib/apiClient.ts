import axios from 'axios';
import type { AxiosInstance, InternalAxiosRequestConfig } from 'axios';

// Create an Axios instance with default config
const apiClient: AxiosInstance = axios.create({
  // Use environment variable for the API base URL
  // This should be defined in .env.local and point to your deployed backend API URL
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Variable to store the getIdToken function
// This will be set by the initializeApiClient function
let _getIdToken: () => Promise<string | null> = async () => null;

/**
 * Initialize the API client with the getIdToken function from the auth context
 * This function should be called once when the app initializes
 * 
 * @param getIdTokenFunc - Function to get the current user's ID token
 */
export const initializeApiClient = (getIdTokenFunc: () => Promise<string | null>): void => {
  _getIdToken = getIdTokenFunc;
};

// Request interceptor to add the auth token to requests
apiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig): Promise<InternalAxiosRequestConfig> => {
    try {
      // Get the current user's ID token
      const token = await _getIdToken();
      
      // If a token is available, add it to the Authorization header
      if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
      } else {
        // Log a warning if no token is available (user not logged in)
        console.warn('No auth token available for API request');
      }
      
      return config;
    } catch (error) {
      console.error('Error getting auth token:', error);
      return config;
    }
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth errors
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    // Check if the error is due to authentication issues
    if (error.response) {
      const status = error.response.status;
      
      if (status === 401 || status === 403) {
        console.error('Authentication error:', error.response.data);
        
        // Here you could add logic to:
        // 1. Redirect to login page
        // 2. Refresh the token
        // 3. Log the user out
        // For now, we'll just log the error
      }
    }
    
    return Promise.reject(error);
  }
);

// Export the API client and initialization function
export default apiClient; 
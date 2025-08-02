import { useAuth } from '@clerk/nextjs';

export const useAuthToken = () => {
  const { getToken, isLoaded, userId } = useAuth();
  
  const getAuthHeaders = async () => {
    const token = await getToken();
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  };

  const getAuthHeadersForFormData = async () => {
    const token = await getToken();
    return {
      'Authorization': `Bearer ${token}`,
      // Don't set Content-Type for FormData - let browser set it
    };
  };

  return {
    getToken,
    getAuthHeaders,
    getAuthHeadersForFormData,
    isLoaded,
    userId,
    isAuthenticated: !!userId,
  };
};

// Helper to create authenticated API calls - use within components
export const createAuthApiCall = <T>(
  callback: (token: string | null) => Promise<T>
) => {
  return async (getToken: () => Promise<string | null>): Promise<T> => {
    const token = await getToken();
    return callback(token);
  };
};
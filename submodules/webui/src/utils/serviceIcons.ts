/**
 * Utility functions for handling service icons in a React application
 * 
 * This module provides functions to retrieve service icons, handle external URLs,
 * and ensure proper URL formatting.
 */


const IMAGE_BASE_URL = process.env.NEXT_PUBLIC_REACT_URL || '/';


// Default service icons with type definitions
export interface ServiceIcon {
  id: string;
  url: string;
}

// Default icons for services (using static imports)
const serviceIcons: Record<string, string> = {
  favicon: 'favicon.ico',
  title: '/images/icons/title.png',
  n8n: '/images/icons/n8n.png',
  openwebui: '/images/icons/openwebui.png',
  chatgpt: '/images/icons/chatgpt.png',
  huggingface: '/images/icons/huggingface.png',
  default: '/images/icons/default-service.png',
};

/**
 * Normalize base URL by ensuring it ends with a slash and handles edge cases
 * @param baseUrl - The base URL to normalize
 * @returns Normalized base URL
 */
const normalizeBaseUrl = (baseUrl: string): string => {
  if (!baseUrl || baseUrl === '/') {
    return '/';
  }

  // Remove trailing slash if present, then add it back
  const cleanUrl = baseUrl.replace(/\/+$/, '');
  return `${cleanUrl}/`;
};

/**
 * Safely join URL path segments
 * @param baseUrl - The base URL
 * @param path - The path to join
 * @returns Properly joined URL
 */
const joinUrlPath = (baseUrl: string, path: string): string => {
  const normalizedBase = normalizeBaseUrl(baseUrl);
  const cleanPath = path.replace(/^\/+/, ''); // Remove leading slashes from path

  return `${normalizedBase}${cleanPath}`;
};

/**
 * Validate if a URL is a valid external URL
 * @param url - The URL to validate
 * @returns True if valid external URL
 */
const isValidExternalUrl = (url: string): boolean => {
  try {
    const parsedUrl = new URL(url);
    return parsedUrl.protocol === 'http:' || parsedUrl.protocol === 'https:';
  } catch {
    return false;
  }
};


/**
 * Get service icon URL with fallback and improved base URL handling
 * 
 * @param serviceId - The service identifier
 * @param externalUrl - Optional external URL to use
 * @returns Local or external image URL
 */
export const getServiceIcon = (serviceId: string, externalUrl?: string): string => {
  // Validate inputs
  if (!serviceId && !externalUrl) {
    console.warn('getServiceIcon called without serviceId or externalUrl');
    return joinUrlPath(IMAGE_BASE_URL, serviceIcons.default);
  }

  // If external URL is provided and valid, use it
  if (externalUrl && isValidExternalUrl(externalUrl)) {
    return externalUrl;
  }

  // If we have a local icon for this service, use it
  if (serviceId && serviceIcons[serviceId]) {
    return joinUrlPath(IMAGE_BASE_URL, serviceIcons[serviceId]);
  }

  // Return default icon as fallback
  return joinUrlPath(IMAGE_BASE_URL, serviceIcons.default);
};

export default serviceIcons;

// Default service icons with type definitions
export interface ServiceIcon {
  id: string;
  url: string;
}

// Default icons for services (using static imports)
const serviceIcons: Record<string, string> = {
  title: '/images/icons/title.png',
  chat: '/images/icons/chat.png',
  embeddings: '/images/icons/embeddings.png',
  audio: '/images/icons/audio.png',
  image: '/images/icons/image.png',
  default: '/images/icons/default-service.png',
};

const IMAGE_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000';

/**
 * Get service icon URL with fallback
 * 
 * @param serviceId - The service identifier
 * @param externalUrl - Optional external URL to use
 * @returns Local or external image URL
 */
export const getServiceIcon = (serviceId: string, externalUrl?: string): string => {
  // If external URL is provided and valid, use it
  if (externalUrl && externalUrl.startsWith('http')) {
    return externalUrl;
  }

  // If we have a local icon for this service, use it
  if (serviceId && serviceIcons[serviceId]) {
    return `${IMAGE_BASE_URL}${serviceIcons[serviceId]}`;
  }

  // Return default icon as fallback
  return `${IMAGE_BASE_URL}${serviceIcons.default}`;
};

export default serviceIcons;

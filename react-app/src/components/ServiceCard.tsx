import React from 'react';
import {
  Card,
  CardContent,
  CardMedia,
  Typography,
  CardActionArea,
  Box,
} from '@mui/material';

/**
 * ServiceCard component represents a service with a title, description, and image.
 * It is clickable and triggers an action when clicked, passing the service ID.
 */
const ServiceCard: React.FC<ServiceCardProps> = ({
  title,
  description,
  imageUrl,
  serviceId,
  onClick,
}) => {
  return (
    <Card
      sx={{
        maxWidth: 345,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        transition: 'transform 0.2s',
        '&:hover': {
          transform: 'scale(1.03)',
        }
      }}
    >
      <CardActionArea
        onClick={() => onClick(serviceId)}
        sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', height: '100%' }}
      >
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'center', position: 'relative', width: 80, height: 80, margin: 'auto' }}>
          <img
            src={imageUrl}
            alt={title}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'contain'
            }}
            loading="lazy"
          />
        </Box>
        <CardContent sx={{ flexGrow: 1 }}>
          <Typography gutterBottom variant="h5" component="div" align="center">
            {title}
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center">
            {description}
          </Typography>
        </CardContent>
      </CardActionArea>
    </Card>
  );
};

/**
 * Props for the ServiceCard component.
 * @property title - The title of the service.
 * @property description - A brief description of the service.
 * @property imageUrl - URL of the image representing the service.
 * @property serviceId - Unique identifier for the service.
 * @property onClick - Callback function triggered when the card is clicked, passing the service ID.
 */
interface ServiceCardProps {
  title: string;
  description: string;
  imageUrl: string;
  serviceId: string;
  onClick: (serviceId: string) => void;
}

export default ServiceCard;

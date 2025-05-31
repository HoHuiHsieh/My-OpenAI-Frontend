import React, { useState } from 'react';
import {
  Container,
  Typography,
  Box,
  Button,
  Paper,
  Grid,
  useTheme,
} from '@mui/material';
import Header from '@/components/Header';
import LoginModal from '@/components/LoginModal';
import ChangePasswordModal from '@/components/ChangePwdModal';
import ServiceCard from '@/components/ServiceCard';
import UsageStats from '@/components/UsageStats';
import { useAuth } from '@/context/AuthContext';
import Head from 'next/head';
import { getServiceIcon } from '@/utils/serviceIcons';
import TokenModal from '@/components/TokenModel';

export default function Home() {
  const [loginModalOpen, setLoginModalOpen] = useState(false);
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [refreshTokenOpen, setRefreshTokenOpen] = useState(false);
  const { isAuthenticated, user, logout } = useAuth();
  const theme = useTheme();

  // Add refresh token function
  const refreshToken = () => {
    setRefreshTokenOpen(true);
  };

  // Handle click events for services
  /**
   * Handles the click event for a service card.
   * @param serviceId - The ID of the clicked service.
   */
  const handleServiceClick = (serviceId: string) => {
    alert(`You clicked on ${serviceId} service. This would navigate to the actual service in a full implementation.`);
  };

  // Sample service data
  const services = [
    {
      id: 'chat',
      title: 'Chat Service',
      description: 'Access AI-powered conversational capabilities',
      image: getServiceIcon('chat', '/images/icons/chat.png'),
    },
    {
      id: 'embeddings',
      title: 'Embeddings',
      description: 'Generate vector embeddings for text and images',
      image: getServiceIcon('embeddings', '/images/icons/embeddings.png'),
    },
    {
      id: 'audio',
      title: 'Speech Services',
      description: 'Text-to-Speech and Speech-to-Text capabilities',
      image: getServiceIcon('audio', '/images/icons/audio.png'),
    },
    {
      id: 'image',
      title: 'Image Generation',
      description: 'Generate images from text descriptions',
      image: getServiceIcon('image', '/images/icons/image.png'),
    },
  ];

  return (
    <>
      <Head>
        <title>AI Platform Portal</title>
        <link rel="icon" href="/favicon.ico" />
      </Head>

      {/* Header component */}
      <Header
        isAuthenticated={isAuthenticated}
        isAdmin={user?.isAdmin}
        username={user?.username}
        onLogin={() => setLoginModalOpen(true)}
        onLogout={logout}
        onRefreshToken={refreshToken}
        onChangePassword={() => setPasswordModalOpen(true)}
      />

      <Container maxWidth="lg" sx={{ mt: 4 }}>
        {/* Welcome section */}
        <Box
          sx={{
            bgcolor: theme.palette.primary.main,
            color: 'white',
            py: 6,
            px: 4,
            borderRadius: 2,
            mb: 4,
            textAlign: 'center',
          }}
        >
          <Typography variant="h3" component="h1" gutterBottom data-testid="welcome-heading">
            Welcome to the AI Platform Portal
          </Typography>
          <Typography variant="h6" component="p">
            Access powerful AI capabilities through a simple interface
          </Typography>
        </Box>

        {/* Conditional rendering based on authentication */}
        {!isAuthenticated ? (
          <Paper
            elevation={3}
            sx={{
              p: 4,
              textAlign: 'center',
              my: 4,
            }}
          >
            <Typography variant="h5" component="h2" gutterBottom>
              Please login to access platform services
            </Typography>
            <Button
              variant="contained"
              color="primary"
              size="large"
              onClick={() => setLoginModalOpen(true)}
              sx={{ mt: 2 }}
            >
              Login
            </Button>
          </Paper>
        ) : (
          <>
            {/* Usage statistics section */}
            <Box sx={{ mb: 5 }}>
              <UsageStats />
            </Box>

            {/* Services section */}
            <Box sx={{ my: 4 }}>
              <Typography
                variant="h4"
                component="h2"
                gutterBottom
                sx={{ mb: 4, textAlign: 'center' }}
              >
                Available Services
              </Typography>
              <Grid container spacing={4}>
                {services.map((service) => (
                  <Grid size={{ xs: 12, sm: 6, md: 3 }} key={service.id}>
                    <ServiceCard
                      title={service.title}
                      description={service.description}
                      imageUrl={service.image}
                      serviceId={service.id}
                      onClick={handleServiceClick}
                    />
                  </Grid>
                ))}
              </Grid>
            </Box>
          </>
        )}

        {/* Modals */}
        <LoginModal open={loginModalOpen} onClose={() => setLoginModalOpen(false)} />
        <ChangePasswordModal open={passwordModalOpen} onClose={() => setPasswordModalOpen(false)} />
        <TokenModal open={refreshTokenOpen} onClose={() => setRefreshTokenOpen(false)} />
      </Container>
    </>
  );
}

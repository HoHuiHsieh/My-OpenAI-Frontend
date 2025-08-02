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
import { useAuthContext } from '@/context/AuthContext';
import Head from 'next/head';
import { getServiceIcon } from '@/utils/serviceIcons';
import TokenModal from '@/components/ApiKeyModel';

const IMAGE_BASE_URL = process.env.NEXT_PUBLIC_API_URL;


/**
 * Main Home component for the AI Platform Portal.
 * @returns 
 */
export default function Home() {
  const [loginModalOpen, setLoginModalOpen] = useState(false);
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [refreshTokenOpen, setRefreshTokenOpen] = useState(false);
  const { isAuthenticated, user, logout } = useAuthContext();
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
    switch (serviceId) {
      case 'Create chat completion':
        window.open('https://platform.openai.com/docs/api-reference/chat/create', '_blank');
        break;
      case 'Create embeddings':
        window.open('https://platform.openai.com/docs/api-reference/embeddings/create', '_blank');
        break;
      case 'llama-3.3-70b-instruct':
        window.open('https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct', '_blank');
        break;
      case 'nv-embed-v2':
        window.open('https://huggingface.co/nvidia/NV-Embed-v2', '_blank');
        break;
      default:
        console.warn(`No action defined for service: ${serviceId}`);
        break;
    }
  };

  // Sample service data
  const services = [
    {
      id: 'Create chat completion',
      title: 'How to create chat completion',
      description: 'OpenAI API Reference',
      image: getServiceIcon('chatgpt', '/images/icons/chatgpt.png'),
    },
    {
      id: 'llama-3.3-70b-instruct',
      title: 'meta/llama-3.3-70b-instruct',
      description: 'Model card for "meta/llama-3.3-70b-instruct" chat model',
      image: getServiceIcon('huggingface', '/images/icons/huggingface.png'),
    },
    {
      id: 'Create embeddings',
      title: 'How to create embeddings',
      description: 'OpenAI API Reference',
      image: getServiceIcon('chatgpt', '/images/icons/chatgpt.png'),
    },
    {
      id: 'nv-embed-v2',
      title: 'nvidia/nv-embed-v2',
      description: 'Model card for "nvidia/nv-embed-v2" embedding model',
      image: getServiceIcon('huggingface', '/images/icons/huggingface.png'),
    },
  ];

  return (
    <>
      <Head>
        <title>AI Platform Portal</title>
        {/* <link rel="icon" href={`${IMAGE_BASE_URL}/favicon.ico`} /> */}
      </Head>

      {/* Header component */}
      <Header
        isAuthenticated={isAuthenticated}
        isAdmin={user.scopes.includes('admin')}
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

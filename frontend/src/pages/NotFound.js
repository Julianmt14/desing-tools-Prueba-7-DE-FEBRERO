import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import HomeIcon from '@mui/icons-material/Home';

const NotFound = () => {
  const navigate = useNavigate();

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        textAlign: 'center',
        p: 3,
      }}
    >
      <Typography
        variant="h1"
        sx={{
          fontSize: { xs: '6rem', md: '8rem' },
          fontWeight: 700,
          color: 'primary.main',
          mb: 2,
        }}
      >
        404
      </Typography>
      
      <Typography
        variant="h4"
        sx={{
          fontWeight: 600,
          mb: 2,
        }}
      >
        Página no encontrada
      </Typography>
      
      <Typography
        variant="body1"
        sx={{
          color: 'text.secondary',
          mb: 4,
          maxWidth: '500px',
        }}
      >
        Lo sentimos, la página que estás buscando no existe o ha sido movida.
      </Typography>
      
      <Button
        variant="contained"
        size="large"
        startIcon={<HomeIcon />}
        onClick={() => navigate('/')}
        sx={{
          borderRadius: 2,
          px: 4,
          py: 1.5,
        }}
      >
        Volver al Inicio
      </Button>
    </Box>
  );
};

export default NotFound;
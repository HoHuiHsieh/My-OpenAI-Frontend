# AI Platform Portal - Next.js Frontend

This is a [Next.js](https://nextjs.org/) project for the AI Platform Portal, replacing the previous static HTML implementation.

## Getting Started

### Setting up the project

Run the setup script to install all dependencies:

```bash
./setup-react-app.sh
```

### Development Server

To start the development server:

```bash
./start.sh react-dev
```

Open [http://localhost:8080](http://localhost:8080) with your browser to see the result.

### Production Build

To create and serve a production build:

```bash
./start.sh react-build
```

## Project Structure

- `src/pages/` - Contains all page components and API routes
- `src/components/` - Reusable components for UI elements like modals and cards
- `src/styles/` - CSS modules for styling
- `src/context/` - React context providers (AuthContext)
- `src/services/` - API service integrations (access, admin, token, usage)
- `src/theme/` - MUI theme configurations
- `src/utils/` - Utility functions and helpers
- `public/` - Static assets like images and icons

## API Integration

The frontend communicates with the backend API to fetch and submit data. API services are organized in the `src/services/` directory, handling authentication, admin functions, token management, and usage statistics.

## Features

- User authentication with login modal and session management
- Dashboard with interactive usage statistics
- Models browsing and integration
- Admin interface with user management capabilities
- Interactive data visualization with Chart.js
- Service cards for different AI capabilities
- Token management system
- Password change functionality

## Key Dependencies

- **Next.js 15** - React framework for production
- **Material UI** - Component library with MUI v7
- **Chart.js** - For interactive data visualization
- **Axios** - HTTP client for API requests
- **Emotion** - CSS-in-JS styling solution

## Available Scripts

- `npm run dev` - Start development server on port 8080
- `npm run build` - Create production build
- `npm run start` - Start production server
- `npm run build-static` - Build and copy static files
- `npm run lint` - Run ESLint

## Learn More

To learn more about Next.js, check out the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

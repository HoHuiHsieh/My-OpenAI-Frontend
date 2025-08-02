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

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

### Production Build

To create and serve a production build:

```bash
./start.sh react-build
```

## Project Structure

- `src/pages/` - Contains all page components and API routes
- `src/components/` - Reusable components
- `src/styles/` - CSS modules for styling
- `public/` - Static assets like images and fonts

## API Integration

The frontend communicates with the backend API to fetch and submit data. Currently, mock API endpoints are included for development purposes.

## Features

- Dashboard with usage statistics
- Models browsing
- Admin interface
- Interactive charts with Chart.js

## Learn More

To learn more about Next.js, check out the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

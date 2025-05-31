FROM node:24-alpine

WORKDIR /workspace

# Install dependencies required for development
RUN apk add git bash

# Install global npm packages
RUN npm install -g next typescript

# Set environment variables
ENV NODE_ENV=development
ENV PORT=3000

# Default command
CMD ["bash"]

# ==========================================
# OceanIQ Frontend - Vite React Dockerfile 
# ==========================================
# Stage 1: Build static assets via Node
FROM node:18-slim AS builder

WORKDIR /app

# Copy package requirements & install
COPY package*.json ./
RUN npm install

# Copy all source files
COPY . .

# Run Vite build to create a static /dist folder
RUN npm run build

# Stage 2: Serve via NGINX (Production)
FROM nginx:alpine

# Copy built assets into nginx public folder
COPY --from=builder /app/dist /usr/share/nginx/html

# Replace standard nginx config with our custom proxy setup
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

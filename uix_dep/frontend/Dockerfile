FROM node:18-alpine
WORKDIR /app

# Copy dependency descriptors first (for cache)
COPY package*.json ./
RUN npm ci

# Copy the rest of your React code
COPY . .

# Expose Vite dev server
ENV VITE_BACKEND_PORT=5000 \
    PORT=5173
EXPOSE 5173

# Launch dev server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
#CMD ["npm", "run", "dev", "--", "--port", "5173"]

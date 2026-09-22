FROM nginx:alpine

# Copy the docs directory to nginx html directory
COPY docs/ /usr/share/nginx/html/

# Expose port 80 (internal use only - accessed via nginx proxy)
EXPOSE 80

# Use nginx's default configuration
CMD ["nginx", "-g", "daemon off;"]

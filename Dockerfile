FROM nginx:alpine

# Copy the docs directory to nginx html directory
COPY docs/ /usr/share/nginx/html/

# Custom nginx config: no-store for html/json so the browser never caches stale app or pending-prints data
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 (internal use only - accessed via nginx proxy)
EXPOSE 80

# Use nginx's default configuration
CMD ["nginx", "-g", "daemon off;"]

# Price Monitor - Live Updates Implementation Guide

This guide explains how to implement automatic price fetching for the Price Monitor feature, eliminating the need for manual price updates.

## Overview

The current Price Monitor uses manual price entry with localStorage storage. This guide outlines a migration to an automated system with:

- **Backend Service**: Docker container for scheduled price fetching
- **API Integration**: Rainforest API (Amazon) and retailer APIs
- **Database Storage**: PostgreSQL for price history
- **REST API**: Endpoint for frontend to consume
- **Configuration**: API key management and scheduling

## Architecture

```
┌─────────────────┐
│ Price Monitor   │ (Frontend - React/HTML)
│   Frontend      │
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│ Price Fetch     │ (Backend Service - Python/Node)
│   Service       │
└────────┬────────┘
         │ API Calls
         ▼
┌─────────────────┐
│ External APIs   │ (Rainforest, Retailers)
│                 │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ PostgreSQL      │ (Price History Database)
│   Database      │
└─────────────────┘
```

## Implementation Steps

### Phase 1: Backend Service Setup

#### 1.1 Create Price Fetch Service Directory

```bash
cd /Users/morganwilkinson/Development/home-server
mkdir price-fetch-service
cd price-fetch-service
```

#### 1.2 Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
```

#### 1.3 Create requirements.txt

```txt
flask==3.0.0
flask-cors==4.0.0
requests==2.31.0
schedule==1.2.0
psycopg2-binary==2.9.9
python-dotenv==1.0.0
rainforest-api==0.1.0
```

#### 1.4 Create app.py (Main Application)

```python
from flask import Flask, jsonify, request
from flask_cors import CORS
import schedule
import time
import threading
import os
from dotenv import load_dotenv
import requests
import psycopg2
from datetime import datetime

load_dotenv()

app = Flask(__name__)
CORS(app)

# Database configuration
DB_HOST = os.getenv('DB_HOST', 'postgres')
DB_NAME = os.getenv('DB_NAME', 'price_monitor')
DB_USER = os.getenv('DB_USER', 'homeuser')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'homedbpassword')
DB_PORT = os.getenv('DB_PORT', '5432')

# API Configuration
RAINFOREST_API_KEY = os.getenv('RAINFOREST_API_KEY', '')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '3600'))  # Default 1 hour

def get_db_connection():
    """Create database connection"""
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )

def init_database():
    """Initialize database tables"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create products table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            brand VARCHAR(100),
            material VARCHAR(50),
            current_price DECIMAL(10, 2),
            target_price DECIMAL(10, 2),
            source VARCHAR(100),
            url TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create price_history table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id SERIAL PRIMARY KEY,
            product_id INTEGER REFERENCES products(id),
            price DECIMAL(10, 2) NOT NULL,
            source VARCHAR(100),
            fetch_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create alerts table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,
            product_id INTEGER REFERENCES products(id),
            type VARCHAR(20),
            message TEXT,
            severity VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            read BOOLEAN DEFAULT FALSE
        )
    """)
    
    conn.commit()
    cur.close()
    conn.close()

# API Routes
@app.route('/api/products', methods=['GET'])
def get_products():
    """Get all products"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products ORDER BY name")
    products = cur.fetchall()
    cur.close()
    conn.close()
    
    return jsonify([{
        'id': p[0],
        'name': p[1],
        'brand': p[2],
        'material': p[3],
        'current_price': float(p[4]),
        'target_price': float(p[5]),
        'source': p[6],
        'url': p[7],
        'notes': p[8],
        'created_at': p[9].isoformat(),
        'updated_at': p[10].isoformat()
    } for p in products])

@app.route('/api/products', methods=['POST'])
def add_product():
    """Add a new product"""
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO products (name, brand, material, current_price, target_price, source, url, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (data['name'], data['brand'], data['material'], 
          data['current_price'], data['target_price'], 
          data['source'], data.get('url'), data.get('notes')))
    
    product_id = cur.fetchone()[0]
    
    # Add initial price history
    cur.execute("""
        INSERT INTO price_history (product_id, price, source)
        VALUES (%s, %s, %s)
    """, (product_id, data['current_price'], 'Initial entry'))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return jsonify({'id': product_id, 'message': 'Product added successfully'})

@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """Update a product"""
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE products 
        SET name=%s, brand=%s, material=%s, current_price=%s, target_price=%s, 
            source=%s, url=%s, notes=%s, updated_at=CURRENT_TIMESTAMP
        WHERE id=%s
    """, (data['name'], data['brand'], data['material'], 
          data['current_price'], data['target_price'], 
          data['source'], data.get('url'), data.get('notes'), product_id))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return jsonify({'message': 'Product updated successfully'})

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Delete a product"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("DELETE FROM products WHERE id=%s", (product_id,))
    conn.commit()
    cur.close()
    conn.close()
    
    return jsonify({'message': 'Product deleted successfully'})

@app.route('/api/price-history/<int:product_id>', methods=['GET'])
def get_price_history(product_id):
    """Get price history for a product"""
    days = request.args.get('days', 30)
    conn = get_db_connection()
    cur = conn.cursor()
    
    if days == 'all':
        cur.execute("""
            SELECT * FROM price_history 
            WHERE product_id=%s 
            ORDER BY fetch_time DESC
        """, (product_id,))
    else:
        cur.execute("""
            SELECT * FROM price_history 
            WHERE product_id=%s AND fetch_time >= NOW() - INTERVAL '%s days'
            ORDER BY fetch_time DESC
        """, (product_id, days))
    
    history = cur.fetchall()
    cur.close()
    conn.close()
    
    return jsonify([{
        'id': h[0],
        'product_id': h[1],
        'price': float(h[2]),
        'source': h[3],
        'fetch_time': h[4].isoformat()
    } for h in history])

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get all alerts"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM alerts ORDER BY created_at DESC")
    alerts = cur.fetchall()
    cur.close()
    conn.close()
    
    return jsonify([{
        'id': a[0],
        'product_id': a[1],
        'type': a[2],
        'message': a[3],
        'severity': a[4],
        'created_at': a[5].isoformat(),
        'read': a[6]
    } for a in alerts])

@app.route('/api/alerts/clear', methods=['POST'])
def clear_alerts():
    """Clear all alerts"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM alerts")
    conn.commit()
    cur.close()
    conn.close()
    
    return jsonify({'message': 'Alerts cleared successfully'})

# Price Fetching Functions
def fetch_amazon_price(asin):
    """Fetch price from Amazon using Rainforest API"""
    if not RAINFOREST_API_KEY:
        return None
    
    try:
        response = requests.get(
            'https://api.rainforestapi.com/request',
            params={
                'api_key': RAINFOREST_API_KEY,
                'type': 'product',
                'amazon_domain': 'amazon.com',
                'asin': asin
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'product' in data and 'price' in data['product']:
                return {
                    'price': float(data['product']['price']['value']),
                    'source': 'Amazon (Rainforest API)'
                }
    except Exception as e:
        print(f"Error fetching Amazon price: {e}")
    
    return None

def fetch_generic_price(url):
    """Attempt to fetch price from generic URL (basic implementation)"""
    # This would need to be expanded with specific retailer APIs
    # For now, return None to indicate manual entry required
    return None

def check_price_updates():
    """Scheduled task to check for price updates"""
    print(f"Checking price updates at {datetime.now()}")
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, current_price, target_price, url FROM products")
    products = cur.fetchall()
    
    for product in products:
        product_id, name, current_price, target_price, url = product
        
        if url and 'amazon' in url.lower():
            # Extract ASIN from Amazon URL
            asin = url.split('/dp/')[1].split('/')[0] if '/dp/' in url else None
            if asin:
                price_data = fetch_amazon_price(asin)
                if price_data:
                    new_price = price_data['price']
                    source = price_data['source']
                    
                    # Check for price change
                    if new_price != current_price:
                        # Update product price
                        cur.execute("""
                            UPDATE products 
                            SET current_price=%s, updated_at=CURRENT_TIMESTAMP 
                            WHERE id=%s
                        """, (new_price, product_id))
                        
                        # Add to price history
                        cur.execute("""
                            INSERT INTO price_history (product_id, price, source)
                            VALUES (%s, %s, %s)
                        """, (product_id, new_price, source))
                        
                        # Check for alerts
                        if new_price <= target_price:
                            cur.execute("""
                                INSERT INTO alerts (product_id, type, message, severity)
                                VALUES (%s, 'target', %s, 'high')
                            """, (product_id, 
                                  f'Price dropped below target! Current: ${new_price:.2f} (Target: ${target_price:.2f})'))
                        
                        drop_percent = ((current_price - new_price) / current_price) * 100
                        if drop_percent >= 10:
                            cur.execute("""
                                INSERT INTO alerts (product_id, type, message, severity)
                                VALUES (%s, 'drop', %s, 'medium')
                            """, (product_id, 
                                  f'Price dropped {drop_percent:.1f}% (from ${current_price:.2f} to ${new_price:.2f})'))
    
    conn.commit()
    cur.close()
    conn.close()

def run_scheduler():
    """Run the scheduled tasks"""
    schedule.every(CHECK_INTERVAL).seconds.do(check_price_updates)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# Start scheduler in background thread
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=5000, debug=False)
```

#### 1.5 Create .env file

```env
# Database Configuration
DB_HOST=postgres
DB_NAME=price_monitor
DB_USER=homeuser
DB_PASSWORD=homedbpassword
DB_PORT=5432

# API Configuration
RAINFOREST_API_KEY=your_rainforest_api_key_here
CHECK_INTERVAL=3600  # Check every hour (in seconds)
```

### Phase 2: Docker Compose Integration

#### 2.1 Update docker-compose.yml

Add the price fetch service to your existing docker-compose.yml:

```yaml
price-fetch:
  build:
    context: ./price-fetch-service
    dockerfile: Dockerfile
  container_name: price-fetch
  # No external port mapping - only accessible via nginx proxy
  environment:
    - DB_HOST=postgres
    - DB_NAME=price_monitor
    - DB_USER=homeuser
    - DB_PASSWORD=homedbpassword
    - DB_PORT=5432
    - RAINFOREST_API_KEY=${RAINFOREST_API_KEY:-}
    - CHECK_INTERVAL=${CHECK_INTERVAL:-3600}
  depends_on:
    - postgres
  restart: unless-stopped
  networks:
    - home-server
```

#### 2.2 Update nginx.conf

Add upstream and server block for the price fetch API:

```nginx
upstream price_fetch {
    server price-fetch:5000;
}

server {
    listen 80;
    server_name price-api.local;

    location / {
        proxy_pass http://price_fetch;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 2.3 Add to hosts file

```
127.0.0.1 price-api.local
```

### Phase 3: Frontend Migration

#### 3.1 Update price-monitor.html

Replace the localStorage-based Store with API calls:

```javascript
// API Configuration
const API_BASE_URL = 'http://price-api.local/api';

// API-based Store
var Store = {
  async init() {
    // No longer need localStorage init
    console.log('API-based store initialized');
  },
  
  async getProducts() {
    try {
      const response = await fetch(`${API_BASE_URL}/products`);
      return await response.json();
    } catch (error) {
      console.error('Failed to fetch products:', error);
      return [];
    }
  },
  
  async addProduct(item) {
    try {
      const response = await fetch(`${API_BASE_URL}/products`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item)
      });
      return await response.json();
    } catch (error) {
      console.error('Failed to add product:', error);
      return null;
    }
  },
  
  async updateProduct(id, updates) {
    try {
      const response = await fetch(`${API_BASE_URL}/products/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      return await response.json();
    } catch (error) {
      console.error('Failed to update product:', error);
      return null;
    }
  },
  
  async deleteProduct(id) {
    try {
      const response = await fetch(`${API_BASE_URL}/products/${id}`, {
        method: 'DELETE'
      });
      return await response.json();
    } catch (error) {
      console.error('Failed to delete product:', error);
      return null;
    }
  },
  
  async getPriceHistory(productId, days) {
    try {
      const url = days === 'all' 
        ? `${API_BASE_URL}/price-history/${productId}?days=all`
        : `${API_BASE_URL}/price-history/${productId}?days=${days}`;
      const response = await fetch(url);
      return await response.json();
    } catch (error) {
      console.error('Failed to fetch price history:', error);
      return [];
    }
  },
  
  async getAlerts() {
    try {
      const response = await fetch(`${API_BASE_URL}/alerts`);
      return await response.json();
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
      return [];
    }
  },
  
  async clearAlerts() {
    try {
      const response = await fetch(`${API_BASE_URL}/alerts/clear`, {
        method: 'POST'
      });
      return await response.json();
    } catch (error) {
      console.error('Failed to clear alerts:', error);
      return null;
    }
  }
};

// Update render functions to use async/await
async function renderWatchList() {
  const products = await Store.getProducts();
  // ... rest of rendering logic
}

// Update all other functions similarly
```

### Phase 4: API Key Setup

#### 4.1 Get Rainforest API Key

1. Sign up at [Rainforest API](https://www.rainforestapi.com/)
2. Get your API key from the dashboard
3. Add it to your .env file or docker-compose environment

#### 4.2 Alternative Retailer APIs

For other retailers, you'll need to implement specific API integrations:

- **Amazon**: Rainforest API (implemented above)
- **eBay**: eBay Browse API
- **AliExpress**: AliExpress Open Platform
- **Generic**: Web scraping with BeautifulSoup (less reliable)

### Phase 5: Testing and Deployment

#### 5.1 Test the Backend Service

```bash
# Build and start the service
cd /Users/morganwilkinson/Development/home-server
docker-compose up -d --build price-fetch

# Check logs
docker-compose logs -f price-fetch

# Test API endpoint
curl http://price-api.local/api/products
```

#### 5.2 Test Price Fetching

Add a test product with an Amazon URL and verify automatic price updates:

```bash
# Add test product via API
curl -X POST http://price-api.local/api/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Product",
    "brand": "Test Brand",
    "material": "PLA",
    "current_price": 29.99,
    "target_price": 25.00,
    "source": "Amazon",
    "url": "https://www.amazon.com/dp/B08X5J7Y9C"
  }'
```

#### 5.3 Update Frontend

After updating price-monitor.html, rebuild the 3D Printer Workshop container:

```bash
docker-compose up -d --build 3d-workshop
```

### Phase 6: Monitoring and Maintenance

#### 6.1 View Price Fetch Logs

```bash
docker-compose logs -f price-fetch
```

#### 6.2 Check Database

```bash
# Connect to PostgreSQL
docker exec -it postgres psql -U homeuser -d price_monitor

# View products
SELECT * FROM products;

# View price history
SELECT * FROM price_history ORDER BY fetch_time DESC LIMIT 10;

# View alerts
SELECT * FROM alerts ORDER BY created_at DESC;
```

#### 6.3 Adjust Check Frequency

Modify the CHECK_INTERVAL in .env or docker-compose.yml:

- `3600` = 1 hour
- `7200` = 2 hours  
- `86400` = 1 day
- `604800` = 1 week

## Advantages of This Approach

1. **Automatic Updates**: No manual price entry required
2. **Reliable Data**: PostgreSQL database for persistent storage
3. **Scalable**: Can handle hundreds of products
4. **API Access**: Other services can integrate with your price data
5. **Scheduled Jobs**: Regular price checks without user intervention
6. **Alert System**: Automatic notifications for price drops

## Troubleshooting

### Issue: API returns 404/500 errors
- Check nginx configuration
- Verify container is running: `docker-compose ps`
- Check logs: `docker-compose logs price-fetch`

### Issue: Price fetching not working
- Verify Rainforest API key is valid
- Check Amazon ASIN extraction logic
- Review fetch logs for specific errors

### Issue: Database connection errors
- Verify PostgreSQL container is running
- Check database credentials in .env
- Ensure database was initialized correctly

### Issue: Frontend not updating
- Clear browser cache
- Check browser console for API errors
- Verify API endpoint is accessible

## Next Steps

1. **Implement additional retailer APIs** for broader coverage
2. **Add authentication** to protect the API endpoint
3. **Create admin dashboard** for monitoring price fetch status
4. **Implement data export** for backup/migration
5. **Add analytics** for price trends and predictions

## Migration Notes

- **Data Migration**: Export existing localStorage data and import via API
- **Backward Compatibility**: Keep localStorage as fallback during transition
- **Testing**: Test thoroughly before removing localStorage implementation
- **Backup**: Always backup existing data before migration

This implementation provides a robust, automated price monitoring system that integrates seamlessly with your existing home server infrastructure.

# 3D Printer Workshop

A collection of web-based tools and resources for 3D printing enthusiasts. This project provides simple, privacy-focused applications that run entirely in your browser with no server requirements.

## Overview

The 3D Printer Workshop is designed to be a lightweight, self-contained toolkit for managing various aspects of 3D printing. Currently, it includes:

### Filament Log
📖 **[Full documentation](docs/pages/filament-log.md)** — data model, localStorage schema, integrations, version history

A comprehensive filament and resin inventory management system that helps you:
- Track spools and refills with detailed specifications
- Monitor material usage and remaining amounts
- Log print jobs with material consumption
- Calculate costs and inventory value
- Set low-stock alerts
- Sync data across devices (optional cloud sync)
- Export/import backups

**Key Features:**
- **Bulk Operations**: Add multiple spools at once or edit multiple spools simultaneously
- **Flexible Views**: Switch between grid and list layouts, with normal or compact card sizes
- **Advanced Sorting**: Sort by name, brand, purchase source, or price
- **Refill Tracking**: Track independent filament rolls (without housing) that can be used to refill empty spools
- **Refill to Spool Conversion**: Convert refills to spools when you load them onto spool housing
- **Sales Tracking**: Track sale prices, original prices, bundle deals, and calculate savings
- **Advanced Analytics**: Three-tier query system (Simple, Medium, Advanced) for deep data analysis
- **Usage Analytics**: View usage statistics and material costs over time
- **Build Plate Compatibility**: Automatic compatibility badges for Bambu Lab X2D build plates (Cool Plate, Engineering Plate, Textured PEI Plate)
- **Build Plate Filtering**: Filter inventory by compatible build plate
- **Print Logging Enhancement**: Track which build plate and plate number were used for each print
- **Auto Print Tracking**: Moonraker / OctoPrint bridge that detects completed prints and lets you import them in one click
- **Price-API Sync**: Auto-push new spools and refills to the home-server Price Monitor with product URL and UPC fields
- **Offline-First**: Works entirely offline with localStorage persistence
- **Optional Cloud Sync**: Firebase integration for cross-device synchronization

### Price Monitor
📖 **[Full documentation](docs/pages/price-monitor.md)** — API endpoints, data model, alert system, known limitations

Track filament prices and get sale alerts for your favorite products:
- Monitor prices across multiple retailers
- Set target prices and receive alerts when items go on sale
- Track price history and trends
- Manual price entry with automatic change calculations
- Configurable alert preferences (in-app, browser, email)
- Export/import price data
- Automatic price fetching via ProductSource API

**Key Features:**
- **Watch List**: Track products you're interested in
- **Price History**: See how prices change over time
- **Smart Alerts**: Get notified when prices drop below target
- **Filtering**: View items on sale, with price drops, or below target
- **Statistics**: Track average price drops and savings
- **Settings**: Configure check frequency and notification methods

### FDM Temperature & Speed Reference
📖 **[Full documentation](docs/pages/fdm-temp-speed-reference.md)** — complete spec tables, troubleshooting index, X2D-specific values

A comprehensive guide for FDM 3D printing settings:
- Material-specific temperature and speed settings
- Troubleshooting guide organized by symptoms
- Print parameters for PLA, PETG, ABS, ASA, TPU, Nylon, PC, PVA, HIPS
- Retraction settings for Bowden and direct-drive systems
- Drying recommendations for different materials
- Print speed and acceleration guidelines

**Key Features:**
- **Quick Reference**: Starting settings for common materials
- **Troubleshooting**: Symptom-based problem solving
- **Detailed Specs**: Nozzle, bed, chamber temps, fan speeds
- **Material Comparison**: Understand differences between filaments
- **Mobile-Friendly**: Optimized for reference during printing

### Filament Cheatsheet
📖 **[Full documentation](docs/pages/filament-cheatsheet.md)** — material profiles, decision guides, content structure

A practical guide for choosing the right filament:
- Material comparison table showing difficulty, strength, heat resistance
- "I want to make X → use Y" quick lookup
- Detailed material profiles with pros and cons
- Best-use recommendations for each material
- Setting guidelines for each filament type

**Key Features:**
- **Decision Guide**: Choose materials based on project requirements
- **Quick Compare**: Easy comparison of material properties
- **Material Profiles**: Detailed information for each filament type
- **Use Cases**: Specific recommendations for common applications
- **Visual Design**: Color-coded materials for easy identification

## Technical Design

### Architecture
The project follows a **single-file architecture** where each tool is a self-contained HTML file that includes:
- HTML structure
- CSS styling (with CSS custom properties for theming)
- JavaScript application logic
- No external dependencies (except optional Firebase for cloud sync)

### Data Persistence
- **Primary Storage**: Browser `localStorage` for offline persistence
- **Backup System**: JSON export/import for data portability
- **Cloud Sync**: Optional Firebase Firestore integration for real-time synchronization across devices

### Design System
The application uses a consistent design system with:
- **CSS Custom Properties**: For easy theming and dark mode support
- **Responsive Design**: Mobile-first approach with breakpoints
- **Accessibility**: Focus states, semantic HTML, keyboard navigation
- **Color Palette**: Neutral, professional design with subtle accent colors

### JavaScript Architecture
The codebase follows a modular pattern within each file:

```javascript
// Data Layer
var Store = {
  spools: [],
  refills: [],
  usage: [],
  // CRUD operations with localStorage persistence
};

// Cloud Sync Layer (Optional)
var CloudSync = {
  // Firebase integration
  // Real-time synchronization
};

// Build Plate Configuration
var BUILD_PLATES = [
  // X2D build plates with material compatibility
];

// UI State Management
var state = {
  // Current view, filters, selections
  // buildPlateFilter for filtering by compatible plate
};

// Rendering Functions
function renderSpoolGrid() { }
function renderStats() { }
// Other view rendering

// Event Handlers
// User interaction handling
```

### File Structure
```
3D Printer Workshop/
├── README.md
├── docs/
│   ├── index.html                         # Main landing page (includes Spoolman link)
│   └── pages/
│       ├── filament-log.html              # Filament inventory tool
│       ├── filament-log.md                # Filament Log documentation
│       ├── price-monitor.html             # Price tracking and alerts
│       ├── price-monitor.md               # Price Monitor documentation
│       ├── fdm-temp-speed-reference.html  # FDM settings reference
│       ├── fdm-temp-speed-reference.md    # FDM reference documentation
│       ├── filament-cheatsheet.html       # Material selection guide
│       ├── filament-cheatsheet.md         # Cheatsheet documentation
│       └── live_updates_price_automation.md # Price automation pipeline docs
```

## Technology Stack

- **HTML5**: Semantic markup and modern web standards
- **CSS3**: Custom properties, Flexbox, Grid, media queries
- **Vanilla JavaScript**: ES6+ features, no frameworks
- **Firebase (Optional)**: Firestore for cloud synchronization
- **LocalStorage API**: Client-side data persistence
- **File API**: For backup export/import functionality

## Terminology

- **Spool**: A complete filament spool with plastic housing and filament ready for printing
- **Refill**: A roll of filament without the spool housing - can be purchased independently and used to refill empty spools
- **Refills are independent**: Can be purchased and tracked without any existing spool of that color or material
- **Conversion**: Refills can be converted to spools when loaded onto empty spool housing

## Analytics System

The Filament Log includes a comprehensive three-tier analytics system:

### Simple Analytics
Pre-built dashboards showing key metrics:
- Total spent and savings from sales
- Purchase breakdowns by source, material, and color
- Average pricing and purchase patterns
- Top vendors, materials, and colors

### Medium Analytics
Query builder for common analyses:
- Select data source (spools, refills, or combined)
- Group by brand, material, color, source, or time period
- Aggregate by count, weight, cost, or savings
- Save and reload common queries

### Advanced Analytics
Custom query system for complex analysis:
- JSON-based filtering for complex conditions
- Custom grouping and aggregation options
- Multiple visualization types (tables, bar charts)
- Query library for saving complex analyses
- Export results to CSV

### Sales Tracking
Track purchase economics:
- Original price vs. sale price
- Bundle information (e.g., "5-pack")
- Unit pricing (per kg, per lb, per spool)
- Automatic savings calculations
- Vendor comparison over time

## Getting Started

### Local Development
1. Clone the repository
2. Open `docs/index.html` in a web browser
3. No build process or server required

### Deployment
The project can be deployed to any static hosting service:
- GitHub Pages
- Netlify
- Vercel
- Any web server

Simply upload the `docs/` directory and you're ready to go.

## Contributing

### Development Guidelines

#### Code Style
- Use consistent indentation (2 spaces)
- Follow existing naming conventions (camelCase for variables/functions)
- Add comments for complex logic
- Keep functions focused and modular

#### Adding New Tools
When adding a new tool to the workshop:

1. **Create a new HTML file** in `docs/pages/`
2. **Follow the existing design system**:
   - Use the same CSS custom properties
   - Match the visual style and components
   - Include dark mode support
3. **Implement data persistence**:
   - Use localStorage for offline storage
   - Provide export/import functionality
   - Consider optional cloud sync
4. **Add to the main index**:
   - Update `docs/index.html` to include the new tool
   - Add appropriate icon and description

#### Modifying Existing Tools

**Storage Changes**: When modifying the data structure:
- Update the `exportJson` version number
- Provide migration logic in `importJson`
- Test with existing user data

**UI Changes**: When modifying the interface:
- Maintain responsive design
- Test on mobile devices
- Ensure accessibility (keyboard navigation, screen readers)
- Preserve dark mode compatibility

### Testing

#### Manual Testing Checklist
- [ ] Test in multiple browsers (Chrome, Firefox, Safari, Edge)
- [ ] Test on mobile devices
- [ ] Test dark/light mode switching
- [ ] Test export/import functionality
- [ ] Test with empty data
- [ ] Test with large datasets
- [ ] Test cloud sync (if applicable)

#### Browser Compatibility
Target browsers:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**PR Requirements:**
- Clear description of changes
- Testing performed
- Screenshot for UI changes (if applicable)
- Follow existing code style

### Future Development Ideas

Potential areas for expansion:
- **Additional Tools**:
  - Print project manager
  - G-code file organizer
  - Printer maintenance log
  - Cost calculator per print
  - Material testing database

- **Enhanced Features**:
  - **Automatic Price Fetching**: API integration for Price Monitor to automatically fetch prices from retailers (Rainforest API for Amazon, official retailer APIs)
  - QR code generation for spool labels
  - Integration with slicer software
  - Advanced analytics and reporting
  - Multi-user support for workshops
  - API for third-party integrations

- **Technical Improvements**:
  - Progressive Web App (PWA) support
  - Offline service worker
  - Database migration system
  - Automated testing framework
  - CI/CD pipeline

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation
- Review the code comments for implementation details

## Acknowledgments

- Design inspiration from modern web applications
- Firebase for cloud sync capabilities
- The 3D printing community for feedback and suggestions
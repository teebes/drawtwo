# DrawTwo Frontend

A Vue 3 + Vite frontend application for the DrawTwo collaborative drawing platform.

## Development

### Prerequisites

- Node.js 20.x or later
- npm

### Local Development (Independent)

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`.

**Note:** For the frontend to work properly, you need the backend running on `http://localhost:8002` (Docker Compose default host port). If you run backend on a different port, set `VITE_API_BASE_URL`.

### Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Docker Development

The frontend can also be run using Docker as part of the full stack:

```bash
# From the root directory
make frontend-dev  # Frontend only
make dev          # Full stack (backend + frontend)
```

## API Integration

The frontend communicates with the Django backend through API endpoints. All requests to `/api/*` are automatically proxied to the backend server during development.

## Project Structure

```
src/
├── components/     # Reusable Vue components
├── views/         # Page components
├── assets/        # Static assets
├── App.vue        # Root component
├── main.js        # Application entry point
└── style.css      # Global styles
```

## Configuration

- **Vite Config**: `vite.config.js` - Contains development server and build settings
- **Package Config**: `package.json` - Dependencies and scripts

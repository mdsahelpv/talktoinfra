# AI Infrastructure Operations Platform Frontend

A modern React application for managing AI infrastructure operations with real-time chat, dashboard analytics, and action execution capabilities.

## Tech Stack

- **React 18** + TypeScript
- **Vite** - Fast build tooling
- **Tailwind CSS** - Utility-first styling
- **shadcn/ui** - Modern UI components
- **React Query** - Server state management
- **Zustand** - Client state management
- **React Router** - Navigation
- **WebSocket** - Real-time updates

## Features

- **JWT Authentication** - Secure login system
- **Chat Interface** - Conversational UI with streaming responses
- **Dashboard** - Overview of system health and activity
- **Actions Panel** - Execute infrastructure operations with approval workflows
- **Real-time Updates** - Live notifications via WebSocket

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
# Navigate to frontend directory
cd /home/ubuntu/talkai/services/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The application will be available at `http://localhost:3000`

### Environment Variables

Create a `.env` file in the frontend directory:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

### Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

### Docker

Build the Docker image:

```bash
docker build -t talkai-frontend .
```

Run the container:

```bash
docker run -p 3000:80 talkai-frontend
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/           # Reusable UI components
│   │   ├── layout/       # Layout components (Sidebar, Header)
│   │   ├── chat/         # Chat-related components
│   │   ├── dashboard/    # Dashboard widgets
│   │   └── actions/      # Action execution components
│   ├── pages/            # Page components
│   ├── hooks/            # Custom React hooks
│   ├── stores/           # Zustand state stores
│   ├── api/              # API client and endpoints
│   ├── types/            # TypeScript type definitions
│   └── utils/            # Utility functions
├── public/               # Static assets
├── Dockerfile            # Multi-stage Docker build
└── package.json          # Dependencies
```

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

### API Integration

The frontend expects a backend API at `/api` with the following endpoints:

- `POST /api/auth/login` - JWT authentication
- `GET /api/chat/history` - Get chat history
- `POST /api/chat/stream` - Stream chat responses
- `GET /api/dashboard/stats` - Dashboard statistics
- `GET /api/actions` - List pending actions
- `POST /api/actions/execute` - Execute actions
- `WS /ws` - WebSocket for real-time updates

## License

MIT

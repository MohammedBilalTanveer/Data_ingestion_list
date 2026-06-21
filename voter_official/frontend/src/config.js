// Central API URL — set VITE_API_URL in .env.local for local dev
// or in the Vercel project environment variables for production.
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

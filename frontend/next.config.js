// Браузер ходит на /api/* этого же сайта, Next.js пересылает запросы в backend (без CORS).
const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";
module.exports = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND}/api/:path*` }];
  },
};

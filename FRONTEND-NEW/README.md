# Frontend Notes

## Required env

- `REACT_APP_API_URL`: optional backend base URL override; production defaults to `/api`

Example local value:
```env
REACT_APP_API_URL=http://localhost:8001
```

## Local development

```bash
cd FRONTEND-NEW
npm install
npm start
```

## Production build

```bash
cd FRONTEND-NEW
npm run build
```

Notes:
- The frontend is intended to be served from `/`
- Report viewing and protected visualizer assets rely on backend auth/session endpoints, so the backend must allow the frontend origin in `ALLOWED_ORIGINS`

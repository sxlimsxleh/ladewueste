/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the API. Default "/api" (proxied to FastAPI by the Vite dev server). */
  readonly VITE_API_BASE?: string;
}

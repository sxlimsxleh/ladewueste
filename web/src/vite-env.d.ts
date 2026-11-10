// Minimal typing for import.meta.env until Vite itself arrives in milestone 5.
interface ImportMeta {
  readonly env?: { readonly VITE_API_BASE?: string };
}

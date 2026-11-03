import { defineConfig } from 'vite';

// Site 100% estático: o build (dist/) é publicado como está (Cloudflare Pages ou qualquer servidor de arquivos)
export default defineConfig({
  base: './',
  build: { outDir: 'dist', emptyOutDir: true },
});

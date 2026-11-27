import { readFileSync } from 'node:fs';
import { fileURLToPath, URL } from 'node:url';

import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { copyFile } from 'wpsjs/vite_plugins';

const templateIcon = { src: '../shared/assets/icons/template.svg', dest: 'images/template.svg' };

// https://vitejs.dev/config/
export default defineConfig({
  base:'./',
  build: {
    assetsInlineLimit: 0
  },
  plugins: [
    copyFile({
      src: 'manifest.xml',
      dest: 'manifest.xml'
    }),
    {
      ...copyFile(templateIcon),
      name: 'wps-template-icon',
      configureServer(server) {
        // The native ribbon requests the same relative path in development and production.
        const source = new URL(templateIcon.src, import.meta.url);
        server.middlewares.use(`/${templateIcon.dest}`, (_req, res) => {
          res.setHeader('Content-Type', 'image/svg+xml');
          res.end(readFileSync(source));
        });
      }
    },
    vue()
  ],
  resolve: {
    dedupe: ['markdown-it'],
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0'
  }
});

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  // Веб-версія: шляхи від кореня сайту. Десктоп (Electron): відносні шляхи.
  base: mode === 'web' ? '/' : './',
}))

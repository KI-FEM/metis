import {defineConfig} from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import {VitePWA} from 'vite-plugin-pwa'
import {fileURLToPath, URL} from 'node:url'
import dotenv from 'dotenv'

dotenv.config()

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vuetify(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'Metis',
        short_name: 'Metis',
        description: 'AI-based coaching for students',
        theme_color: '#1e6586',
        background_color: '#f6fafe',
        categories: ['education'],
        screenshots: [
          {
            src: 'screenshots/narrow_topics.png',
            sizes: '1170x2532',
            form_factor: 'narrow',
            label: 'Screenshot showing the available themes'
          },
          {
            src: 'screenshots/narrow_topics_selected.png',
            sizes: '1170x2532',
            form_factor: 'narrow',
            label: 'Screenshot showing the configuration of a topic'
          },
          {
            src: 'screenshots/narrow_chat.png',
            sizes: '1170x2532',
            form_factor: 'narrow',
            label: 'Screenshot showing a chat history'
          },
          {
            src: 'screenshots/wide_topics.png',
            sizes: '2048x1536',
            form_factor: 'wide',
            label: 'Screenshot showing the available themes'
          },
          {
            src: 'screenshots/wide_topics_selected.png',
            sizes: '2048x1536',
            form_factor: 'wide',
            label: 'Screenshot showing the configuration of a topic'
          },
          {
            src: 'screenshots/wide_chat.png',
            sizes: '2048x1536',
            form_factor: 'wide',
            label: 'Screenshot showing a chat history'
          }
        ]
      },
      pwaAssets: {
        overrideManifestIcons: true
      }
    })
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    outDir: '../public'
  },
  base: process.env.VITE_BASE_URL || '/'
})

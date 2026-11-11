import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({plugins:[react()],server:{watch:{usePolling:true,interval:500},proxy:{'/api':'http://127.0.0.1:48123'}},build:{rollupOptions:{output:{manualChunks:{charts:['recharts']}}}}});

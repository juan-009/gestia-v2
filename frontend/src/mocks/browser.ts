import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'

export const worker = setupWorker(...handlers); 


// Asegura que el código se ejecute solo en el navegador.
if (typeof window !== 'undefined') {
  worker.start({
    serviceWorker: {
      url: '/mockServiceWorker.js', // Ruta absoluta a la raíz
    },
  });
}

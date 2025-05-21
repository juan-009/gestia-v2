import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.tsx';
import './index.css';

async function enableMocking() {
  if (process.env.NODE_ENV !== 'development') {
    return;
  }

  if (!('serviceWorker' in navigator)) {
    console.warn('Service workers are not supported. MSW will not be enabled.');
    return;
  }

  if (navigator.serviceWorker) {
    try {
      const { worker } = await import('./mocks/browser');
      await worker.start({
        onUnhandledRequest: 'bypass',
      });
    } catch (error) {
      console.error('Error starting MSW worker:', error);
    }
  } else {
    console.warn('navigator.serviceWorker is not available. MSW will not be enabled.');
  }
}

enableMocking().then(() => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>
  );
});
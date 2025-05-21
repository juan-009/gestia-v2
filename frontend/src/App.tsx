import React, { useEffect } from 'react';
import { Provider } from 'react-redux';
import { PersistGate } from 'redux-persist/integration/react';
import { store, persistor } from './store/store';
import Routes from './routes';
import ToastContainer from './components/ui/ToastContainer';
import { useDispatch, useSelector } from 'react-redux';
import { setTheme, selectTheme } from './features/ui/uiSlice';

// Theme setup component
const ThemeSetup: React.FC = () => {
  const dispatch = useDispatch();
  const theme = useSelector(selectTheme);
  
  useEffect(() => {
    // Initial theme setup
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else if (theme === 'light') {
      document.documentElement.classList.remove('dark');
    } else if (theme === 'system') {
      // Check system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      if (prefersDark) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
      
      // Listen for system preference changes
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = (e: MediaQueryListEvent) => {
        if (e.matches) {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
      };
      
      mediaQuery.addEventListener('change', handleChange);
      return () => {
        mediaQuery.removeEventListener('change', handleChange);
      };
    }
  }, [theme, dispatch]);
  
  return null;
};

// App with Redux providers
const AppWithRedux: React.FC = () => {
  return (
    <Provider store={store}>
      <PersistGate loading={null} persistor={persistor}>
        <AppContent />
      </PersistGate>
    </Provider>
  );
};

// App content
const AppContent: React.FC = () => {
  return (
    <>
      <ThemeSetup />
      <Routes />
      <ToastContainer />
    </>
  );
};

export default AppWithRedux;
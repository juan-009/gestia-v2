import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Home, ArrowLeft } from 'lucide-react';
import Button from '../components/ui/Button';

const NotFound: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex flex-col items-center justify-center px-4">
      <div className="max-w-md w-full text-center">
        <div className="text-6xl font-bold text-gray-900 dark:text-white mb-2">404</div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
          Page Not Found
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mb-8">
          Sorry, we couldn't find the page you're looking for. The page might have been removed,
          renamed, or is temporarily unavailable.
        </p>
        <div className="space-y-4">
          <Button
            onClick={() => navigate('/')}
            leftIcon={<Home className="h-5 w-5" />}
            fullWidth
          >
            Go to Homepage
          </Button>
          <Button
            variant="secondary"
            onClick={() => navigate(-1)}
            leftIcon={<ArrowLeft className="h-5 w-5" />}
            fullWidth
          >
            Go Back
          </Button>
        </div>
      </div>
    </div>
  );
};

export default NotFound;
import React from 'react';
import { useSelector } from 'react-redux';
import { selectUser } from '../features/auth/authSlice';
import { useGetUserProfileQuery } from '../features/user/userApi';
import { Activity, Users, Shield, Clock } from 'lucide-react';
import Alert from '../components/ui/Alert';

const Dashboard: React.FC = () => {
  const user = useSelector(selectUser);
  const { data: profile, isLoading, error } = useGetUserProfileQuery();

  const stats = [
    {
      name: 'Active Sessions',
      value: '3',
      icon: Activity,
      change: '+5%',
      changeType: 'increase',
    },
    {
      name: 'Team Members',
      value: '12',
      icon: Users,
      change: '+2',
      changeType: 'increase',
    },
    {
      name: 'Security Score',
      value: '98',
      icon: Shield,
      change: '+10',
      changeType: 'increase',
    },
    {
      name: 'Last Activity',
      value: '2m ago',
      icon: Clock,
      change: 'Active',
      changeType: 'neutral',
    },
  ];

  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-1/4 mb-4"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-32 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="error" title="Error loading dashboard">
        Failed to load dashboard data. Please try again later.
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Welcome back, {user?.firstName || 'User'}!
        </h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <div
            key={stat.name}
            className="bg-white dark:bg-gray-800 overflow-hidden rounded-lg shadow"
          >
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <stat.icon className="h-6 w-6 text-gray-400" aria-hidden="true" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      {stat.name}
                    </dt>
                    <dd className="flex items-baseline">
                      <div className="text-2xl font-semibold text-gray-900 dark:text-white">
                        {stat.value}
                      </div>
                      <div className={`ml-2 flex items-baseline text-sm font-semibold ${
                        stat.changeType === 'increase' 
                          ? 'text-green-600' 
                          : stat.changeType === 'decrease' 
                            ? 'text-red-600'
                            : 'text-gray-500'
                      }`}>
                        {stat.change}
                      </div>
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Recent Activity
          </h2>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="flex items-center text-sm text-gray-500 dark:text-gray-400"
              >
                <div className="w-2 h-2 bg-blue-500 rounded-full mr-2"></div>
                <span>Activity item {i + 1}</span>
                <span className="ml-auto">{i + 1}m ago</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Quick Actions
          </h2>
          <div className="grid grid-cols-2 gap-4">
            {['View Profile', 'Security Settings', 'Team Management', 'Support'].map((action) => (
              <button
                key={action}
                className="flex items-center justify-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                {action}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
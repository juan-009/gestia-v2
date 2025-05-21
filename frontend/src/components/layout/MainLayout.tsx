import React from 'react';
import { Outlet } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { selectAuth } from '../../features/auth/authSlice';
import { 
  Users, 
  FileText, 
  Home, 
  User, 
  LogOut,
  Menu,
  X
} from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { logout } from '../../features/auth/authSlice';

const MainLayout: React.FC = () => {
  const { user } = useSelector(selectAuth);
  const location = useLocation();
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = React.useState(false);

  const handleLogout = () => {
    dispatch(logout());
    navigate('/auth/login');
  };

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  const NavLink: React.FC<{ to: string; icon: React.ReactNode; label: string }> = ({ 
    to, 
    icon, 
    label 
  }) => (
    <Link
      to={to}
      className={`flex items-center gap-2 p-3 rounded-lg transition-colors ${
        isActive(to)
          ? 'bg-indigo-600 text-white'
          : 'text-gray-600 hover:bg-indigo-50 hover:text-indigo-600'
      }`}
    >
      {icon}
      <span>{label}</span>
    </Link>
  );

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-20 bg-black bg-opacity-50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside 
        className={`fixed inset-y-0 left-0 z-30 w-64 transform bg-white shadow-lg transition-transform duration-200 ease-in-out lg:static lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-20 items-center justify-between px-6">
          <div className="flex items-center gap-2">
            <div className="rounded-lg bg-indigo-600 p-2 text-white">
              <FileText size={24} />
            </div>
            <h1 className="text-xl font-bold text-gray-900">SecureApp</h1>
          </div>
          <button 
            className="lg:hidden" 
            onClick={() => setSidebarOpen(false)}
          >
            <X className="h-6 w-6 text-gray-500" />
          </button>
        </div>

        <nav className="mt-6 px-4 space-y-1">
          <NavLink to="/dashboard" icon={<Home className="h-5 w-5" />} label="Dashboard" />
          <NavLink to="/profile" icon={<User className="h-5 w-5" />} label="Profile" />
          
          {user && user.role === 'admin' && (
            <>
              <NavLink to="/users" icon={<Users className="h-5 w-5" />} label="User Management" />
              <NavLink to="/audit-logs" icon={<FileText className="h-5 w-5" />} label="Audit Logs" />
            </>
          )}
          
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-2 p-3 text-gray-600 hover:bg-red-50 hover:text-red-600 rounded-lg transition-colors"
          >
            <LogOut className="h-5 w-5" />
            <span>Logout</span>
          </button>
        </nav>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-white shadow-sm">
          <div className="flex h-16 items-center justify-between px-4">
            <button 
              className="rounded-md p-2 text-gray-500 hover:bg-gray-100 lg:hidden"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="h-6 w-6" />
            </button>
            
            <div className="flex items-center gap-3">
              <div className="relative">
                {user && (
                  <div className="flex items-center gap-2">
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-100 text-indigo-600">
                      {user.name?.charAt(0) || 'U'}
                    </div>
                    <div className="hidden md:block">
                      <p className="text-sm font-medium text-gray-700">{user.name || 'User'}</p>
                      <p className="text-xs text-gray-500">{user.email}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* Main content area */}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>

        {/* Footer */}
        <footer className="bg-white p-4 text-center text-sm text-gray-500 shadow-inner">
          &copy; {new Date().getFullYear()} GestIa Tech - All Rights Reserved
        </footer>
      </div>
    </div>
  );
};

export default MainLayout;
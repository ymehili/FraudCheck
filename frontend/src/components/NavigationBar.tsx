'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { UserButton, useUser } from '@clerk/nextjs';
import { 
  Shield, 
  Upload, 
  BarChart3, 
  History, 
  Menu, 
  X 
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { ROUTES } from '@/lib/constants';

const navigation = [
  { name: 'Dashboard', href: ROUTES.DASHBOARD, icon: BarChart3 },
  { name: 'Upload', href: ROUTES.UPLOAD, icon: Upload },
  { name: 'History', href: ROUTES.HISTORY, icon: History },
];

export function NavigationBar() {
  const pathname = usePathname();
  const { user, isLoaded } = useUser();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Don't show navigation on the home page for unauthenticated users
  if (pathname === '/' && !user) {
    return null;
  }

  return (
    <nav className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo and brand */}
          <div className="flex">
            <Link href={user ? ROUTES.DASHBOARD : ROUTES.HOME} className="flex-shrink-0 flex items-center">
              <Shield className="h-8 w-8 text-blue-600" />
              <span className="ml-2 text-xl font-bold text-gray-900">
                CheckGuard AI
              </span>
            </Link>
            
            {/* Desktop navigation */}
            {user && (
              <div className="hidden sm:ml-8 sm:flex sm:space-x-8">
                {navigation.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.href || 
                    pathname.startsWith(item.href + '/');
                  
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={cn(
                        'inline-flex items-center px-1 pt-1 text-sm font-medium border-b-2 transition-colors',
                        isActive
                          ? 'border-blue-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      )}
                    >
                      <Icon className="h-4 w-4 mr-2" />
                      {item.name}
                    </Link>
                  );
                })}
              </div>
            )}
          </div>

          {/* Right side - User menu and mobile menu button */}
          <div className="flex items-center">
            {isLoaded && user ? (
              <>
                {/* User button for authenticated users */}
                <div className="flex items-center space-x-4">
                  <span className="hidden sm:block text-sm text-gray-700">
                    {user.emailAddresses[0]?.emailAddress}
                  </span>
                  <UserButton 
                    appearance={{
                      elements: {
                        avatarBox: 'w-8 h-8',
                      },
                    }}
                  />
                </div>

                {/* Mobile menu button */}
                <div className="sm:hidden ml-4">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                    className="inline-flex items-center justify-center p-2"
                  >
                    <span className="sr-only">Open main menu</span>
                    {mobileMenuOpen ? (
                      <X className="block h-6 w-6" />
                    ) : (
                      <Menu className="block h-6 w-6" />
                    )}
                  </Button>
                </div>
              </>
            ) : isLoaded ? (
              /* Sign-in button for unauthenticated users */
              <div className="flex items-center space-x-4">
                <Link href="/sign-in">
                  <Button>Sign In</Button>
                </Link>
              </div>
            ) : (
              /* Loading state */
              <div className="w-8 h-8 rounded-full bg-gray-200 animate-pulse" />
            )}
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && user && (
        <div className="sm:hidden">
          <div className="pt-2 pb-3 space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || 
                pathname.startsWith(item.href + '/');
              
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={cn(
                    'flex items-center pl-3 pr-4 py-2 text-base font-medium transition-colors',
                    isActive
                      ? 'bg-blue-50 border-r-4 border-blue-500 text-blue-700'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  )}
                >
                  <Icon className="h-5 w-5 mr-3" />
                  {item.name}
                </Link>
              );
            })}
          </div>
          
          {/* Mobile user info */}
          <div className="pt-4 pb-3 border-t border-gray-200">
            <div className="flex items-center px-4">
              <div className="text-base font-medium text-gray-800">
                {user.firstName} {user.lastName}
              </div>
            </div>
            <div className="px-4">
              <div className="text-sm text-gray-500">
                {user.emailAddresses[0]?.emailAddress}
              </div>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
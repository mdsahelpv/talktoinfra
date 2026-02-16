import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  MessageSquare,
  LayoutDashboard,
  Play,
  CheckCircle,
  Settings,
  Menu,
  ChevronLeft,
  LogOut,
  Bot,
  Server,
} from 'lucide-react';
import { cn } from '@/utils';
import { useAuthStore, useUIStore } from '@/stores';
import { Button, CommandPalette } from '@/components/ui';

const navItems = [
  { path: '/chat', label: 'Chat', icon: MessageSquare },
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/infra', label: 'Infra', icon: Server },
  { path: '/actions', label: 'Actions', icon: Play },
  { path: '/approvals', label: 'Approvals', icon: CheckCircle },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export default function Layout() {
  const { sidebarOpen, toggleSidebar } = useUIStore();
  const { logout, user } = useAuthStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="flex h-screen bg-background">
      {/* Desktop Sidebar */}
      <aside
        className={cn(
          'hidden lg:flex flex-col border-r bg-card transition-all duration-300',
          sidebarOpen ? 'w-64' : 'w-16'
        )}
      >
        {/* Logo */}
        <div className="flex h-16 items-center justify-between border-b px-4">
          <div className="flex items-center gap-2 overflow-hidden">
            <Bot className="h-6 w-6 shrink-0 text-primary" />
            {sidebarOpen && (
              <span className="font-semibold whitespace-nowrap">TalkAI</span>
            )}
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className="shrink-0"
          >
            <ChevronLeft
              className={cn(
                'h-4 w-4 transition-transform',
                !sidebarOpen && 'rotate-180'
              )}
            />
          </Button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-auto py-4">
          <ul className="space-y-1 px-2">
            {navItems.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                      !sidebarOpen && 'justify-center'
                    )
                  }
                >
                  <item.icon className="h-5 w-5 shrink-0" />
                  {sidebarOpen && <span className="whitespace-nowrap">{item.label}</span>}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* User & Logout */}
        <div className="border-t p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-medium shrink-0">
              {user?.username?.charAt(0).toUpperCase() || 'U'}
            </div>
            {sidebarOpen && (
              <div className="flex-1 min-w-0 overflow-hidden">
                <p className="text-sm font-medium truncate">{user?.username}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {user?.roles?.join(', ') || 'No role'}
                </p>
              </div>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={logout}
              className="shrink-0"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </aside>

      {/* Mobile Header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 flex h-16 items-center justify-between border-b bg-card px-4">
        <div className="flex items-center gap-2">
          <Bot className="h-6 w-6 text-primary" />
          <span className="font-semibold">TalkAI</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-48">
            <CommandPalette />
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            <Menu className="h-6 w-6" />
          </Button>
        </div>
      </div>

      {/* Desktop Header with Command Palette */}
      <div className="hidden lg:flex fixed top-0 left-64 right-0 z-40 h-16 items-center justify-between border-b bg-card/95 backdrop-blur px-6">
        <CommandPalette />
        <div className="flex items-center gap-2">
          {/* Onboarding Progress Indicator */}
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-40 bg-background pt-16">
          <nav className="p-4">
            <ul className="space-y-2">
              {navItems.map((item) => (
                <li key={item.path}>
                  <NavLink
                    to={item.path}
                    onClick={() => setMobileMenuOpen(false)}
                    className={({ isActive }) =>
                      cn(
                        'flex items-center gap-3 rounded-md px-4 py-3 text-sm font-medium transition-colors',
                        isActive
                          ? 'bg-primary text-primary-foreground'
                          : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                      )
                    }
                  >
                    <item.icon className="h-5 w-5" />
                    <span>{item.label}</span>
                  </NavLink>
                </li>
              ))}
            </ul>
            <div className="mt-4 border-t pt-4">
              <Button
                variant="ghost"
                className="w-full justify-start gap-3"
                onClick={() => {
                  setMobileMenuOpen(false);
                  logout();
                }}
              >
                <LogOut className="h-5 w-5" />
                <span>Logout</span>
              </Button>
            </div>
          </nav>
        </div>
      )}

      {/* Main Content */}
      <main className="flex-1 overflow-auto lg:pt-16 pt-16">
        <div className="h-full p-4 lg:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

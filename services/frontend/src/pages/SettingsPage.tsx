import { useState } from 'react';
import {
  User,
  Bell,
  Shield,
  Database,
  Moon,
  Sun,
  ChevronRight,
  Save,
  Scan,
  Brain,
} from 'lucide-react';
import InfrastructureDiscovery from '@/components/settings/InfrastructureDiscovery';
import AISettings from '@/pages/Settings/AISettings';
import toast from 'react-hot-toast';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  Input,
  Badge,
} from '@/components/ui';
import { useAuthStore, useThemeStore } from '@/stores';

export default function SettingsPage() {
  const { user } = useAuthStore();  // isAdmin removed - TODO: Re-enable when implementing proper authorization
  const { isDark, toggleTheme } = useThemeStore();
  const [notifications, setNotifications] = useState(true);

  const handleSave = () => {
    toast.success('Settings saved');
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Manage your account and application preferences
        </p>
      </div>

      {/* Profile Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Profile
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium">Username</label>
              <Input value={user?.username || ''} disabled />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Email</label>
              <Input value={user?.email || ''} disabled />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">Roles: {user?.roles?.join(', ') || 'None'}</Badge>
          </div>
        </CardContent>
      </Card>

      {/* Preferences Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Preferences
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-primary/10 p-2">
                <Bell className="h-4 w-4 text-primary" />
              </div>
              <div>
                <p className="font-medium">Notifications</p>
                <p className="text-sm text-muted-foreground">
                  Receive notifications for important events
                </p>
              </div>
            </div>
            <Button
              variant={notifications ? 'default' : 'outline'}
              size="sm"
              onClick={() => setNotifications(!notifications)}
            >
              {notifications ? 'Enabled' : 'Disabled'}
            </Button>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-primary/10 p-2">
                {isDark ? (
                  <Moon className="h-4 w-4 text-primary" />
                ) : (
                  <Sun className="h-4 w-4 text-primary" />
                )}
              </div>
              <div>
                <p className="font-medium">Theme</p>
                <p className="text-sm text-muted-foreground">
                  {isDark ? 'Dark mode' : 'Light mode'}
                </p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={toggleTheme}
            >
              {isDark ? 'Switch to Light' : 'Switch to Dark'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Security Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Security
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-primary/10 p-2">
                <Shield className="h-4 w-4 text-primary" />
              </div>
              <div>
                <p className="font-medium">Change Password</p>
                <p className="text-sm text-muted-foreground">
                  Update your account password
                </p>
              </div>
            </div>
            <Button variant="outline" size="sm">
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-primary/10 p-2">
                <Database className="h-4 w-4 text-primary" />
              </div>
              <div>
                <p className="font-medium">API Keys</p>
                <p className="text-sm text-muted-foreground">
                  Manage API access tokens
                </p>
              </div>
            </div>
            <Button variant="outline" size="sm">
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Infrastructure Discovery Section */}
      {/* TODO: Implement proper authorization in future */}
      {/* Currently all authenticated users can access infrastructure discovery */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Scan className="h-5 w-5" />
            Infrastructure Discovery
            {/* Admin Only badge removed - add back when implementing authorization */}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <InfrastructureDiscovery />
        </CardContent>
      </Card>

      {/* AI Engine Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5" />
            AI Engine
          </CardTitle>
        </CardHeader>
        <CardContent>
          <AISettings />
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave}>
          <Save className="mr-2 h-4 w-4" />
          Save Changes
        </Button>
      </div>
    </div>
  );
}

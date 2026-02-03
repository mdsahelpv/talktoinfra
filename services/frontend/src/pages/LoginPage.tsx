import { useState } from 'react';
import { Bot, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { Button, Input, Card, CardContent } from '@/components/ui';
import { useAuth } from '@/hooks/useAuth';
import { authApi, apiClient } from '@/api/client';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      toast.error('Please enter both username and password');
      return;
    }

    setIsLoading(true);
    try {
      const authResponse = await authApi.login({ username, password });
      // Set token immediately so getProfile can use it
      apiClient.setToken(authResponse.access_token);
      const profile = await authApi.getProfile();
      login(profile, authResponse.access_token);
      toast.success('Welcome back!');
    } catch (error) {
      console.error('Login error:', error);
      toast.error(error instanceof Error ? error.message : 'Invalid credentials');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardContent className="pt-6">
          <div className="flex flex-col items-center space-y-6">
            <div className="flex items-center space-x-2">
              <Bot className="h-10 w-10 text-primary" />
              <span className="text-2xl font-bold">TalkAI</span>
            </div>
            
            <div className="text-center">
              <h1 className="text-2xl font-semibold">Welcome back</h1>
              <p className="text-sm text-muted-foreground">
                Sign in to access your infrastructure operations
              </p>
            </div>

            <form onSubmit={handleSubmit} className="w-full space-y-4">
              <div className="space-y-2">
                <label htmlFor="username" className="text-sm font-medium">
                  Username
                </label>
                <Input
                  id="username"
                  type="text"
                  placeholder="Enter your username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={isLoading}
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="password" className="text-sm font-medium">
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                />
              </div>

              <Button
                type="submit"
                className="w-full"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  'Sign in'
                )}
              </Button>
            </form>

            <p className="text-xs text-muted-foreground text-center">
              Infrastructure Operations Platform
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

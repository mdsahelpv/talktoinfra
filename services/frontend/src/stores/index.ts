import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, Message, ChatSession, Action } from '@/types';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean; // Track rehydration state
  isAdmin: () => boolean;
  login: (user: User, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: true, // Initially loading until rehydrated
      isAdmin: () => {
        // TODO: Implement proper authorization in future
        // Currently all authenticated users have admin access
        const user = get().user;
        return user !== null; // All authenticated users are treated as admin
      },
      login: (user, token) => set({ user, token, isAuthenticated: true, isLoading: false }),
      logout: () => set({ user: null, token: null, isAuthenticated: false, isLoading: false }),
    }),
    {
      name: 'auth-storage',
      onRehydrateStorage: () => (state) => {
        // Mark as loaded after rehydration
        if (state) {
          state.isLoading = false;
        }
      },
    }
  )
);

interface ChatState {
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  isLoading: boolean;
  addMessage: (sessionId: string, message: Message) => void;
  updateMessage: (sessionId: string, messageId: string, updates: Partial<Message>) => void;
  setCurrentSession: (session: ChatSession | null) => void;
  createSession: () => ChatSession;
  setLoading: (loading: boolean) => void;
}

export const useChatStore = create<ChatState>()((set, get) => ({
  sessions: [],
  currentSession: null,
  isLoading: false,
  addMessage: (sessionId, message) => {
    set((state) => ({
      sessions: state.sessions.map((session) =>
        session.id === sessionId
          ? { ...session, messages: [...session.messages, message], updatedAt: new Date().toISOString() }
          : session
      ),
      currentSession:
        get().currentSession?.id === sessionId
          ? { ...get().currentSession!, messages: [...get().currentSession!.messages, message] }
          : get().currentSession,
    }));
  },
  updateMessage: (sessionId, messageId, updates) => {
    set((state) => ({
      sessions: state.sessions.map((session) =>
        session.id === sessionId
          ? {
            ...session,
            messages: session.messages.map((m) => (m.id === messageId ? { ...m, ...updates } : m)),
          }
          : session
      ),
    }));
  },
  setCurrentSession: (session) => set({ currentSession: session }),
  createSession: () => {
    const newSession: ChatSession = {
      id: Math.random().toString(36).substring(2, 15),
      title: 'New Conversation',
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    set((state) => ({
      sessions: [newSession, ...state.sessions],
      currentSession: newSession,
    }));
    return newSession;
  },
  setLoading: (loading) => set({ isLoading: loading }),
}));

interface ActionState {
  actions: Action[];
  pendingActions: Action[];
  addAction: (action: Action) => void;
  updateAction: (actionId: string, updates: Partial<Action>) => void;
  approveAction: (actionId: string, approvedBy: string) => void;
  rejectAction: (actionId: string) => void;
}

export const useActionStore = create<ActionState>()((set) => ({
  actions: [],
  pendingActions: [],
  addAction: (action) =>
    set((state) => {
      const newActions = [action, ...state.actions];
      return {
        actions: newActions,
        pendingActions: newActions.filter((a) => a.status === 'pending'),
      };
    }),
  updateAction: (actionId, updates) =>
    set((state) => {
      const newActions = state.actions.map((a) => (a.id === actionId ? { ...a, ...updates } : a));
      return {
        actions: newActions,
        pendingActions: newActions.filter((a) => a.status === 'pending'),
      };
    }),
  approveAction: (actionId, approvedBy) =>
    set((state) => {
      const newActions = state.actions.map((a) =>
        a.id === actionId ? { ...a, status: 'approved' as const, approvedBy } : a
      );
      return {
        actions: newActions,
        pendingActions: newActions.filter((a) => a.status === 'pending'),
      };
    }),
  rejectAction: (actionId) =>
    set((state) => {
      const newActions = state.actions.map((a) =>
        a.id === actionId ? { ...a, status: 'rejected' as const } : a
      );
      return {
        actions: newActions,
        pendingActions: newActions.filter((a) => a.status === 'pending'),
      };
    }),
}));

interface UIState {
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>()((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}));

// Theme Store for Dark/Light Mode
interface ThemeState {
  isDark: boolean;
  toggleTheme: () => void;
  setDarkMode: (isDark: boolean) => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      isDark: true, // Default to dark mode
      toggleTheme: () => {
        const newMode = !get().isDark;
        get().setDarkMode(newMode);
      },
      setDarkMode: (isDark) => {
        // Apply to document
        if (isDark) {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
        set({ isDark });
      },
    }),
    {
      name: 'theme-storage',
      onRehydrateStorage: () => (state) => {
        // Apply theme when store is rehydrated from localStorage
        if (state) {
          if (state.isDark) {
            document.documentElement.classList.add('dark');
          } else {
            document.documentElement.classList.remove('dark');
          }
        }
      },
    }
  )
);

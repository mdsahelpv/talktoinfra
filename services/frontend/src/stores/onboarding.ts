import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface OnboardingStep {
    id: string;
    title: string;
    description: string;
    completed: boolean;
    route?: string;
}

export interface OnboardingProgress {
    currentStep: number;
    totalSteps: number;
    startedAt: string | null;
    completedAt: string | null;
    steps: OnboardingStep[];
}

interface OnboardingState {
    isOnboardingComplete: boolean;
    progress: OnboardingProgress;
    isVisible: boolean;

    // Actions
    startOnboarding: () => void;
    completeStep: (stepId: string) => void;
    skipOnboarding: () => void;
    setVisible: (visible: boolean) => void;
    resetOnboarding: () => void;
}

const defaultSteps: OnboardingStep[] = [
    {
        id: 'welcome',
        title: 'Welcome to TalkAI',
        description: 'Get started with infrastructure management',
        completed: false,
    },
    {
        id: 'connect-cluster',
        title: 'Connect Your First Cluster',
        description: 'Add a Kubernetes cluster to manage',
        completed: false,
        route: '/onboarding',
    },
    {
        id: 'discover-resources',
        title: 'Discover Resources',
        description: 'Scan and catalog your infrastructure',
        completed: false,
        route: '/infra',
    },
    {
        id: 'explore-chat',
        title: 'Try the Chat Interface',
        description: 'Ask questions about your infrastructure',
        completed: false,
        route: '/chat',
    },
    {
        id: 'setup-alerts',
        title: 'Set Up Monitoring',
        description: 'Configure alerts for your resources',
        completed: false,
        route: '/monitoring',
    },
    {
        id: 'complete',
        title: 'You\'re All Set!',
        description: 'Start managing your infrastructure',
        completed: false,
    },
];

const getInitialProgress = (): OnboardingProgress => ({
    currentStep: 0,
    totalSteps: defaultSteps.length,
    startedAt: null,
    completedAt: null,
    steps: defaultSteps.map(step => ({ ...step })),
});

export const useOnboardingStore = create<OnboardingState>()(
    persist(
        (set, get) => ({
            isOnboardingComplete: false,
            progress: getInitialProgress(),
            isVisible: false,

            startOnboarding: () => {
                const now = new Date().toISOString();
                set((state) => ({
                    isVisible: true,
                    progress: {
                        ...state.progress,
                        startedAt: now,
                        currentStep: 0,
                        steps: state.progress.steps.map((step, idx) => ({
                            ...step,
                            completed: idx === 0,
                        })),
                    },
                }));
            },

            completeStep: (stepId: string) => {
                set((state) => {
                    const stepIndex = state.progress.steps.findIndex(s => s.id === stepId);
                    if (stepIndex === -1) return state;

                    const newSteps = state.progress.steps.map((step, idx) => ({
                        ...step,
                        completed: idx <= stepIndex ? true : step.completed,
                    }));

                    const nextStep = stepIndex + 1;
                    const isComplete = nextStep >= state.progress.totalSteps;

                    return {
                        isOnboardingComplete: isComplete,
                        isVisible: !isComplete,
                        progress: {
                            ...state.progress,
                            currentStep: isComplete ? state.progress.currentStep : nextStep,
                            completedAt: isComplete ? new Date().toISOString() : null,
                            steps: newSteps,
                        },
                    };
                });
            },

            skipOnboarding: () => {
                set({
                    isOnboardingComplete: true,
                    isVisible: false,
                });
            },

            setVisible: (visible: boolean) => {
                set({ isVisible: visible });
            },

            resetOnboarding: () => {
                set({
                    isOnboardingComplete: false,
                    progress: getInitialProgress(),
                    isVisible: true,
                });
            },
        }),
        {
            name: 'onboarding-storage',
        }
    )
);

// Hook to check if user should see onboarding
export const useShouldShowOnboarding = (): boolean => {
    const { isOnboardingComplete, progress } = useOnboardingStore();

    // Show onboarding if not complete and hasn't been started
    if (isOnboardingComplete) return false;
    if (progress.startedAt) return false;

    return true;
};

// Hook to get current onboarding step
export const useCurrentOnboardingStep = (): OnboardingStep | null => {
    const { progress } = useOnboardingStore();
    return progress.steps[progress.currentStep] || null;
};

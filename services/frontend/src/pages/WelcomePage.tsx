import { useNavigate } from 'react-router-dom';
import { useOnboardingStore, useCurrentOnboardingStep } from '@/stores/onboarding';
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Progress } from '@/components/ui';
import {
    Rocket,
    Server,
    Search,
    MessageSquare,
    Bell,
    CheckCircle2,
    ArrowRight,
    ArrowLeft,
    SkipForward
} from 'lucide-react';
import { useEffect, useState } from 'react';

const stepIcons: Record<string, React.ReactNode> = {
    'welcome': <Rocket className="w-8 h-8" />,
    'connect-cluster': <Server className="w-8 h-8" />,
    'discover-resources': <Search className="w-8 h-8" />,
    'explore-chat': <MessageSquare className="w-8 h-8" />,
    'setup-alerts': <Bell className="w-8 h-8" />,
    'complete': <CheckCircle2 className="w-8 h-8" />,
};

const stepColors: Record<string, string> = {
    'welcome': 'from-purple-500 to-indigo-600',
    'connect-cluster': 'from-blue-500 to-cyan-600',
    'discover-resources': 'from-green-500 to-emerald-600',
    'explore-chat': 'from-orange-500 to-amber-600',
    'setup-alerts': 'from-red-500 to-rose-600',
    'complete': 'from-green-500 to-teal-600',
};

export default function WelcomePage() {
    const navigate = useNavigate();
    const {
        progress,
        completeStep,
        skipOnboarding,
        startOnboarding,
        isOnboardingComplete
    } = useOnboardingStore();
    const currentStep = useCurrentOnboardingStep();
    const [isAnimating, setIsAnimating] = useState(false);

    // Start onboarding when page loads
    useEffect(() => {
        if (!progress.startedAt) {
            startOnboarding();
        }
    }, [progress.startedAt, startOnboarding]);

    const handleNext = () => {
        if (!currentStep) return;

        setIsAnimating(true);

        // Navigate to the step's route if it has one
        if (currentStep.route) {
            completeStep(currentStep.id);
            navigate(currentStep.route);
        } else if (currentStep.id === 'complete') {
            completeStep(currentStep.id);
            navigate('/dashboard');
        } else {
            completeStep(currentStep.id);
        }

        setTimeout(() => setIsAnimating(false), 300);
    };

    const handleSkip = () => {
        skipOnboarding();
        navigate('/dashboard');
    };

    const handlePrevious = () => {
        const prevStep = progress.currentStep - 1;
        if (prevStep >= 0) {
            setIsAnimating(true);
            // Navigate to previous step's route
            const prevStepData = progress.steps[prevStep];
            if (prevStepData.route) {
                navigate(prevStepData.route);
            }
            setTimeout(() => setIsAnimating(false), 300);
        }
    };

    const progressPercent = ((progress.currentStep + 1) / progress.totalSteps) * 100;

    if (isOnboardingComplete) {
        navigate('/dashboard');
        return null;
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
            <div className="max-w-2xl w-full">
                {/* Logo and Title */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-indigo-600 mb-4">
                        <Rocket className="w-8 h-8 text-white" />
                    </div>
                    <h1 className="text-4xl font-bold text-white mb-2">Welcome to TalkAI</h1>
                    <p className="text-slate-400 text-lg">Your AI-powered infrastructure management platform</p>
                </div>

                {/* Progress Bar */}
                <div className="mb-8">
                    <div className="flex justify-between text-sm text-slate-400 mb-2">
                        <span>Step {progress.currentStep + 1} of {progress.totalSteps}</span>
                        <span>{Math.round(progressPercent)}% complete</span>
                    </div>
                    <Progress value={progressPercent} className="h-2" />
                </div>

                {/* Main Card */}
                <Card className={`bg-slate-800/50 border-slate-700 backdrop-blur-sm transition-all duration-300 ${isAnimating ? 'opacity-50 scale-95' : 'opacity-100 scale-100'}`}>
                    <CardHeader className="text-center pb-4">
                        <div className={`inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br ${stepColors[currentStep?.id || 'welcome']} mx-auto mb-4`}>
                            <div className="text-white">
                                {stepIcons[currentStep?.id || 'welcome']}
                            </div>
                        </div>
                        <CardTitle className="text-2xl text-white">{currentStep?.title}</CardTitle>
                        <CardDescription className="text-slate-400 text-base">
                            {currentStep?.description}
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        {/* Step Indicators */}
                        <div className="flex justify-center gap-2">
                            {progress.steps.map((step, idx) => (
                                <div
                                    key={step.id}
                                    className={`w-3 h-3 rounded-full transition-all duration-300 ${idx === progress.currentStep
                                        ? 'bg-purple-500 scale-125'
                                        : step.completed
                                            ? 'bg-green-500'
                                            : 'bg-slate-600'
                                        }`}
                                />
                            ))}
                        </div>

                        {/* Feature Highlights */}
                        <div className="grid grid-cols-2 gap-4 mt-6">
                            {getStepFeatures(currentStep?.id || 'welcome').map((feature, idx) => (
                                <div
                                    key={idx}
                                    className="flex items-start gap-3 p-3 rounded-lg bg-slate-700/30"
                                >
                                    <CheckCircle2 className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
                                    <span className="text-slate-300 text-sm">{feature}</span>
                                </div>
                            ))}
                        </div>

                        {/* Action Buttons */}
                        <div className="flex justify-between gap-4 mt-8">
                            <Button
                                variant="outline"
                                onClick={handlePrevious}
                                disabled={progress.currentStep === 0}
                                className="border-slate-600 text-slate-300 hover:bg-slate-700"
                            >
                                <ArrowLeft className="w-4 h-4 mr-2" />
                                Back
                            </Button>

                            <Button
                                variant="ghost"
                                onClick={handleSkip}
                                className="text-slate-400 hover:text-white hover:bg-slate-700"
                            >
                                Skip
                                <SkipForward className="w-4 h-4 ml-2" />
                            </Button>

                            <Button
                                onClick={handleNext}
                                className="bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 text-white"
                            >
                                {currentStep?.route ? 'Go' : 'Continue'}
                                <ArrowRight className="w-4 h-4 ml-2" />
                            </Button>
                        </div>
                    </CardContent>
                </Card>

                {/* Keyboard Shortcut Hint */}
                <p className="text-center text-slate-500 text-sm mt-6">
                    Press <kbd className="px-2 py-1 rounded bg-slate-700 text-slate-300 text-xs">Esc</kbd> to skip
                </p>
            </div>
        </div>
    );
}

function getStepFeatures(stepId: string): string[] {
    const features: Record<string, string[]> = {
        'welcome': [
            'Connect Kubernetes clusters',
            'Discover infrastructure automatically',
            'Chat with AI about your resources',
            'Set up smart monitoring alerts',
        ],
        'connect-cluster': [
            'Support for multiple K8s clusters',
            'Secure credential management',
            'Real-time connection testing',
            'Auto-discovery of existing clusters',
        ],
        'discover-resources': [
            'Scan pods, services, and deployments',
            'Detect running databases and caches',
            'Map network services and ports',
            'Track resource relationships',
        ],
        'explore-chat': [
            'Natural language queries',
            'Get instant infrastructure insights',
            'Request actions with approval',
            'View resource details instantly',
        ],
        'setup-alerts': [
            'Real-time health monitoring',
            'Custom alert rules',
            'Multiple notification channels',
            'Auto-healing recommendations',
        ],
        'complete': [
            'Full infrastructure visibility',
            'AI-powered insights',
            'Automated monitoring',
            'Continuous optimization',
        ],
    };

    return features[stepId] || [];
}

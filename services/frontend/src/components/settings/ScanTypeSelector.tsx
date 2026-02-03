import React from 'react';
import { Zap, Search, ScanLine, Layers, CheckCircle2, AlertCircle, Info } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui';
import { cn } from '@/utils';

type ScannerType = 'python' | 'fast' | 'detailed' | 'hybrid';

interface ScannerOption {
  id: ScannerType;
  name: string;
  description: string;
  icon: React.ReactNode;
  pros: string[];
  cons: string[];
  recommendedFor: string;
  available: boolean;
}

const SCANNER_OPTIONS: ScannerOption[] = [
  {
    id: 'python',
    name: 'Python Async',
    description: 'Pure Python implementation with asyncio for concurrent port scanning',
    icon: <ScanLine className="h-6 w-6" />,
    pros: ['No external dependencies', 'Cross-platform', 'Good for small to medium networks'],
    cons: ['Slower than native tools', 'Higher resource usage'],
    recommendedFor: 'Small networks (/24 or smaller), development environments',
    available: true,
  },
  {
    id: 'fast',
    name: 'Fast (Masscan)',
    description: 'Ultra-fast port scanning using Masscan - can scan the entire internet in minutes',
    icon: <Zap className="h-6 w-6" />,
    pros: ['Extremely fast', 'Can handle large networks', 'Low memory footprint'],
    cons: ['Requires root privileges', 'May trigger IDS/IPS', 'Less accurate service detection'],
    recommendedFor: 'Large networks (/16 or larger), quick reconnaissance',
    available: true,
  },
  {
    id: 'detailed',
    name: 'Detailed (Nmap)',
    description: 'Comprehensive scanning with Nmap including service detection and OS fingerprinting',
    icon: <Search className="h-6 w-6" />,
    pros: ['Accurate service detection', 'OS fingerprinting', 'Script scanning support'],
    cons: ['Slower than Masscan', 'Requires Nmap installation', 'More network noise'],
    recommendedFor: 'Detailed reconnaissance, service identification, security audits',
    available: true,
  },
  {
    id: 'hybrid',
    name: 'Hybrid',
    description: 'Combines Masscan for host discovery with Nmap for detailed service detection',
    icon: <Layers className="h-6 w-6" />,
    pros: ['Best of both worlds', 'Fast host discovery', 'Detailed service info'],
    cons: ['Requires both tools', 'Complex configuration', 'Longer total scan time'],
    recommendedFor: 'Enterprise networks, comprehensive assessments',
    available: true,
  },
];

interface ScanTypeSelectorProps {
  selected: ScannerType;
  onSelect: (type: ScannerType) => void;
  networkSize?: number;
  className?: string;
}

function getRecommendedScanner(networkSize?: number): ScannerType {
  if (!networkSize) return 'python';
  
  if (networkSize <= 256) {
    return 'python';
  } else if (networkSize <= 4096) {
    return 'fast';
  } else if (networkSize <= 65536) {
    return 'hybrid';
  } else {
    return 'fast';
  }
}

export default function ScanTypeSelector({ 
  selected, 
  onSelect, 
  networkSize,
  className 
}: ScanTypeSelectorProps) {
  const recommended = getRecommendedScanner(networkSize);

  return (
    <div className={cn('space-y-4', className)}>
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Info className="h-4 w-4" />
        <span>Select the scanner that best fits your network size and requirements</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {SCANNER_OPTIONS.map((scanner) => {
          const isSelected = selected === scanner.id;
          const isRecommended = recommended === scanner.id;

          return (
            <Card
              key={scanner.id}
              className={cn(
                'cursor-pointer transition-all duration-200 relative overflow-hidden',
                isSelected 
                  ? 'border-primary ring-2 ring-primary/20' 
                  : 'hover:border-primary/50',
                !scanner.available && 'opacity-60 cursor-not-allowed'
              )}
              onClick={() => scanner.available && onSelect(scanner.id)}
            >
              {isRecommended && (
                <div className="absolute top-0 right-0 bg-primary text-primary-foreground text-xs px-2 py-1 rounded-bl-lg font-medium">
                  Recommended
                </div>
              )}
              
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      'p-2 rounded-lg',
                      isSelected ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'
                    )}>
                      {scanner.icon}
                    </div>
                    <div>
                      <CardTitle className="text-base">{scanner.name}</CardTitle>
                      <CardDescription className="text-xs mt-0.5">
                        {scanner.description}
                      </CardDescription>
                    </div>
                  </div>
                  
                  <div className={cn(
                    'h-5 w-5 rounded-full border-2 flex items-center justify-center',
                    isSelected ? 'border-primary bg-primary' : 'border-muted-foreground'
                  )}>
                    {isSelected && <CheckCircle2 className="h-3 w-3 text-primary-foreground" />}
                  </div>
                </div>
              </CardHeader>
              
              <CardContent className="pt-0">
                <div className="space-y-3">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1">Pros:</p>
                    <ul className="space-y-0.5">
                      {scanner.pros.map((pro, idx) => (
                        <li key={idx} className="text-xs flex items-center gap-1 text-green-600">
                          <CheckCircle2 className="h-3 w-3" />
                          {pro}
                        </li>
                      ))}
                    </ul>
                  </div>
                  
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1">Cons:</p>
                    <ul className="space-y-0.5">
                      {scanner.cons.map((con, idx) => (
                        <li key={idx} className="text-xs flex items-center gap-1 text-orange-600">
                          <AlertCircle className="h-3 w-3" />
                          {con}
                        </li>
                      ))}
                    </ul>
                  </div>
                  
                  <div className="pt-2 border-t">
                    <p className="text-xs text-muted-foreground">
                      <span className="font-medium">Best for:</span> {scanner.recommendedFor}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

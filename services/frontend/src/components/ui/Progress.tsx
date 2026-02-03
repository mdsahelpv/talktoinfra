import { cn } from '@/utils';

interface ProgressProps {
  value: number;
  className?: string;
}

export default function Progress({ value, className }: ProgressProps) {
  return (
    <div className={cn('h-2 w-full overflow-hidden rounded-full bg-secondary', className)}>
      <div
        className="h-full bg-primary transition-all duration-300 ease-in-out"
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}

import { Metadata } from 'next';
import ComparisonDashboard from '@/components/comparisons/ComparisonDashboard';

export const metadata: Metadata = {
  title: 'Comparison Views | Shadower Analytics',
  description: 'Side-by-side comparison views for agents, periods, workspaces, and metrics',
};

export default function ComparisonsPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <ComparisonDashboard />
    </div>
  );
}

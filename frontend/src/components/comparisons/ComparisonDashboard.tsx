'use client';

import React, { useState } from 'react';
import { ComparisonType } from '@/types/comparison-views';
import AgentComparisonView from './AgentComparisonView';
import PeriodComparisonView from './PeriodComparisonView';
import WorkspaceComparisonView from './WorkspaceComparisonView';
import MetricComparisonView from './MetricComparisonView';

interface ComparisonDashboardProps {
  defaultType?: ComparisonType;
}

export default function ComparisonDashboard({
  defaultType = 'agents',
}: ComparisonDashboardProps) {
  const [selectedType, setSelectedType] = useState<ComparisonType>(defaultType);

  const tabs: { type: ComparisonType; label: string; description: string }[] = [
    {
      type: 'agents',
      label: 'Agent Comparison',
      description: 'Compare performance across multiple agents',
    },
    {
      type: 'periods',
      label: 'Period Comparison',
      description: 'Compare current vs. previous period',
    },
    {
      type: 'workspaces',
      label: 'Workspace Comparison',
      description: 'Compare metrics across workspaces',
    },
    {
      type: 'metrics',
      label: 'Metric Comparison',
      description: 'Deep dive into specific metrics',
    },
  ];

  const renderComparisonView = () => {
    switch (selectedType) {
      case 'agents':
        return <AgentComparisonView />;
      case 'periods':
        return <PeriodComparisonView />;
      case 'workspaces':
        return <WorkspaceComparisonView />;
      case 'metrics':
        return <MetricComparisonView />;
      default:
        return <div>Select a comparison type</div>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Comparison Views</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          Side-by-side analysis to identify differences and improvements
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex space-x-8" aria-label="Tabs">
          {tabs.map((tab) => (
            <button
              key={tab.type}
              onClick={() => setSelectedType(tab.type)}
              className={`
                py-4 px-1 border-b-2 font-medium text-sm transition-colors
                ${
                  selectedType === tab.type
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }
              `}
            >
              <div className="flex flex-col items-start">
                <span>{tab.label}</span>
                <span className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {tab.description}
                </span>
              </div>
            </button>
          ))}
        </nav>
      </div>

      {/* Comparison View Content */}
      <div className="mt-6">{renderComparisonView()}</div>
    </div>
  );
}

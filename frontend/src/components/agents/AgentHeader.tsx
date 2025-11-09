/**
 * Agent Header Component
 * Displays agent information and action buttons
 */

import React from 'react';
import { AgentAnalytics } from '@/types/agent-analytics';
import { Button } from '@/components/ui/Button';

interface AgentHeaderProps {
  agent: AgentAnalytics;
  onExport?: () => void;
  onShare?: () => void;
}

export function AgentHeader({ agent, onExport, onShare }: AgentHeaderProps) {
  return (
    <div className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              Agent Analytics
            </h1>
            <p className="mt-2 text-sm text-gray-600">
              Agent ID: <span className="font-mono text-gray-900">{agent.agentId}</span>
            </p>
            <p className="text-sm text-gray-500 mt-1">
              Last updated: {new Date(agent.generatedAt).toLocaleString()}
            </p>
          </div>

          <div className="flex gap-3">
            {onExport && (
              <Button
                onClick={onExport}
                variant="outline"
                className="flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Export
              </Button>
            )}
            {onShare && (
              <Button
                onClick={onShare}
                variant="outline"
                className="flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                </svg>
                Share
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

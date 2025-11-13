/**
 * Lifecycle Status Card Component
 *
 * Displays the current lifecycle state with visual indicator
 */

'use client';

import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { STATE_COLORS, AgentState } from '@/types/agent-lifecycle';

export interface LifecycleStatusCardProps {
  currentState: string;
  currentStateSince: string;
  daysInCurrentState: number;
  className?: string;
}

export function LifecycleStatusCard({
  currentState,
  currentStateSince,
  daysInCurrentState,
  className = '',
}: LifecycleStatusCardProps) {
  const stateKey = currentState.toUpperCase() as keyof typeof AgentState;
  const colors = STATE_COLORS[AgentState[stateKey]] || STATE_COLORS[AgentState.DRAFT];

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return dateString;
    }
  };

  return (
    <Card className={className}>
      <CardContent className="pt-6">
        <div className="space-y-3">
          <p className="text-sm font-medium text-muted-foreground">Current State</p>

          <div
            className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-semibold border-2 ${colors.bg} ${colors.text} ${colors.border}`}
          >
            <span className={`w-2 h-2 rounded-full mr-2 ${colors.text.replace('text-', 'bg-')}`} />
            {currentState.toUpperCase()}
          </div>

          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">
              Since {formatDate(currentStateSince)}
            </p>
            <p className="text-sm font-medium">
              {daysInCurrentState.toFixed(0)} days in this state
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

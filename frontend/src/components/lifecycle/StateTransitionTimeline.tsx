/**
 * State Transition Timeline Component
 *
 * Visualizes the sequence of state transitions over time
 */

'use client';

import React from 'react';
import { StateTransition, LifecycleTimeline } from '@/types/agent-lifecycle';

export interface StateTransitionTimelineProps {
  transitions: StateTransition[];
  timeline: LifecycleTimeline[];
  className?: string;
}

export function StateTransitionTimeline({
  transitions,
  timeline,
  className = '',
}: StateTransitionTimelineProps) {
  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateString;
    }
  };

  if (transitions.length === 0) {
    return (
      <div className={`text-center py-8 text-muted-foreground ${className}`}>
        No state transitions recorded yet
      </div>
    );
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {transitions.slice(0, 10).map((transition, index) => (
        <div key={index} className="flex items-start gap-4 pb-3 border-b last:border-0">
          <div className="flex-shrink-0 w-24 text-xs text-muted-foreground">
            {formatDate(transition.transitionAt)}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              {transition.fromState && (
                <>
                  <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs font-medium capitalize">
                    {transition.fromState}
                  </span>
                  <span className="text-muted-foreground">→</span>
                </>
              )}
              <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium capitalize">
                {transition.toState}
              </span>
            </div>
            {transition.transitionReason && (
              <p className="text-xs text-muted-foreground">{transition.transitionReason}</p>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              Triggered by: {transition.triggeredBy}
            </p>
          </div>
        </div>
      ))}
      {transitions.length > 10 && (
        <p className="text-xs text-center text-muted-foreground pt-2">
          Showing 10 of {transitions.length} transitions
        </p>
      )}
    </div>
  );
}

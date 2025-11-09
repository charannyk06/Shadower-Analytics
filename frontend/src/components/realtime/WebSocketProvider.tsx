'use client';

import React, { createContext, useContext } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAuth } from '@/contexts/AuthContext';

interface WebSocketContextType {
  sendMessage: (message: any) => void;
  subscribe: (eventTypes: string[]) => void;
  unsubscribe: (eventTypes: string[]) => void;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  reconnect: () => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(
  undefined
);

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();

  const websocket = useWebSocket({
    workspaceId: user?.workspaceId,
    autoReconnect: true,
    maxReconnectAttempts: 5,
  });

  return (
    <WebSocketContext.Provider value={websocket}>
      {children}
    </WebSocketContext.Provider>
  );
}

export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error(
      'useWebSocketContext must be used within WebSocketProvider'
    );
  }
  return context;
};

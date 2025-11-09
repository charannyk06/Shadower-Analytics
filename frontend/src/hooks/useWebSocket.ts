import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';

interface WebSocketOptions {
  workspaceId?: string;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onMessage?: (event: MessageEvent) => void;
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
}

interface WebSocketHook {
  sendMessage: (message: any) => void;
  subscribe: (eventTypes: string[]) => void;
  unsubscribe: (eventTypes: string[]) => void;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  reconnect: () => void;
}

export function useWebSocket(options: WebSocketOptions = {}): WebSocketHook {
  const {
    workspaceId,
    autoReconnect = true,
    reconnectInterval = 1000,
    maxReconnectAttempts = 5,
    onMessage,
    onOpen,
    onClose,
    onError,
  } = options;

  const { token, user } = useAuth();
  const [connectionStatus, setConnectionStatus] = useState<
    'connecting' | 'connected' | 'disconnected' | 'error'
  >('disconnected');

  const ws = useRef<WebSocket | null>(null);
  const reconnectCount = useRef(0);
  const reconnectTimeout = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    if (!token) {
      console.error('No auth token available');
      return;
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = process.env.NEXT_PUBLIC_API_URL
      ? process.env.NEXT_PUBLIC_API_URL.replace(/^https?:\/\//, '')
      : 'localhost:8000';
    const wsUrl = new URL(`${wsProtocol}//${wsHost}/ws`);

    wsUrl.searchParams.append('token', token);

    if (workspaceId) {
      wsUrl.searchParams.append('workspace_id', workspaceId);
    }

    setConnectionStatus('connecting');

    try {
      ws.current = new WebSocket(wsUrl.toString());

      ws.current.onopen = (event) => {
        setConnectionStatus('connected');
        reconnectCount.current = 0;
        console.log('WebSocket connected');

        // Send initial subscriptions
        if (ws.current?.readyState === WebSocket.OPEN) {
          ws.current.send(
            JSON.stringify({
              type: 'subscribe',
              event_types: [
                'execution_started',
                'execution_completed',
                'metrics_update',
                'alert',
                'agent_status_change',
                'workspace_update',
              ],
            })
          );
        }

        onOpen?.(event);
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket message:', data);

          // Handle specific event types
          switch (data.event) {
            case 'connected':
              console.log('Connection confirmed:', data.connection_id);
              break;

            case 'execution_completed':
              // Could trigger a refetch of metrics
              console.log('Execution completed:', data.data);
              break;

            case 'alert':
              console.log('Alert received:', data.data);
              // Could show toast notification based on priority
              break;

            case 'error':
              console.error('WebSocket error message:', data.error);
              break;
          }

          onMessage?.(event);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.current.onclose = (event) => {
        setConnectionStatus('disconnected');
        console.log('WebSocket disconnected:', event.code, event.reason);

        // Auto reconnect logic
        if (autoReconnect && reconnectCount.current < maxReconnectAttempts) {
          const delay = reconnectInterval * Math.pow(2, reconnectCount.current);
          reconnectCount.current++;

          console.log(
            `Reconnecting in ${delay}ms (attempt ${reconnectCount.current})`
          );

          reconnectTimeout.current = setTimeout(() => {
            connect();
          }, delay);
        } else if (reconnectCount.current >= maxReconnectAttempts) {
          console.error('Max reconnection attempts reached');
          setConnectionStatus('error');
        }

        onClose?.(event);
      };

      ws.current.onerror = (event) => {
        setConnectionStatus('error');
        console.error('WebSocket error:', event);
        onError?.(event);
      };
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      setConnectionStatus('error');
    }
  }, [
    token,
    workspaceId,
    autoReconnect,
    reconnectInterval,
    maxReconnectAttempts,
    onMessage,
    onOpen,
    onClose,
    onError,
  ]);

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
    }

    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      console.error('WebSocket not connected');
    }
  }, []);

  const subscribe = useCallback(
    (eventTypes: string[]) => {
      sendMessage({
        type: 'subscribe',
        event_types: eventTypes,
      });
    },
    [sendMessage]
  );

  const unsubscribe = useCallback(
    (eventTypes: string[]) => {
      sendMessage({
        type: 'unsubscribe',
        event_types: eventTypes,
      });
    },
    [sendMessage]
  );

  const reconnect = useCallback(() => {
    disconnect();
    reconnectCount.current = 0;
    connect();
  }, [connect, disconnect]);

  // Connect on mount
  useEffect(() => {
    if (!token) {
      return;
    }

    connect();

    // Heartbeat
    const heartbeatInterval = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // Every 30 seconds

    return () => {
      clearInterval(heartbeatInterval);
      disconnect();
    };
  }, [token, connect, disconnect]);

  return {
    sendMessage,
    subscribe,
    unsubscribe,
    connectionStatus,
    reconnect,
  };
}

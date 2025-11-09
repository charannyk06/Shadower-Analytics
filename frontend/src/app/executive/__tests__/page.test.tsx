/**
 * Tests for Executive Dashboard Page
 */

import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ExecutivePage from '../page';
import * as useMetricsHook from '@/hooks/api/useMetrics';

// Mock the useMetrics hook
jest.mock('@/hooks/api/useMetrics');

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('ExecutivePage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should display loading state', () => {
    jest.spyOn(useMetricsHook, 'useMetrics').mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      isError: false,
      isSuccess: false,
    } as any);

    render(<ExecutivePage />, { wrapper: createWrapper() });

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('should display error state', () => {
    jest.spyOn(useMetricsHook, 'useMetrics').mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
      isError: true,
      isSuccess: false,
    } as any);

    render(<ExecutivePage />, { wrapper: createWrapper() });

    expect(screen.getByText(/error loading metrics/i)).toBeInTheDocument();
  });

  it('should display metrics when loaded successfully', () => {
    const mockMetrics = {
      mrr: 50000,
      dau: 100,
      mau: 1500,
    };

    jest.spyOn(useMetricsHook, 'useMetrics').mockReturnValue({
      data: mockMetrics,
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
    } as any);

    render(<ExecutivePage />, { wrapper: createWrapper() });

    expect(screen.getByText('Executive Dashboard')).toBeInTheDocument();
    expect(screen.getByText('MRR')).toBeInTheDocument();
    expect(screen.getByText('$50000')).toBeInTheDocument();
    expect(screen.getByText('DAU')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
    expect(screen.getByText('MAU')).toBeInTheDocument();
    expect(screen.getByText('1500')).toBeInTheDocument();
  });

  it('should display zero values when metrics are not available', () => {
    const mockMetrics = {
      mrr: undefined,
      dau: undefined,
      mau: undefined,
    };

    jest.spyOn(useMetricsHook, 'useMetrics').mockReturnValue({
      data: mockMetrics,
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
    } as any);

    render(<ExecutivePage />, { wrapper: createWrapper() });

    expect(screen.getByText('$0')).toBeInTheDocument();
    expect(screen.getAllByText('0')).toHaveLength(2); // DAU and MAU show 0
  });

  it('should have correct grid layout', () => {
    const mockMetrics = {
      mrr: 50000,
      dau: 100,
      mau: 1500,
    };

    jest.spyOn(useMetricsHook, 'useMetrics').mockReturnValue({
      data: mockMetrics,
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
    } as any);

    const { container } = render(<ExecutivePage />, {
      wrapper: createWrapper(),
    });

    const grid = container.querySelector('.grid.grid-cols-3');
    expect(grid).toBeInTheDocument();
  });

  it('should display metric cards with proper styling', () => {
    const mockMetrics = {
      mrr: 50000,
      dau: 100,
      mau: 1500,
    };

    jest.spyOn(useMetricsHook, 'useMetrics').mockReturnValue({
      data: mockMetrics,
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
    } as any);

    const { container } = render(<ExecutivePage />, {
      wrapper: createWrapper(),
    });

    const cards = container.querySelectorAll('.bg-white.rounded-lg.shadow');
    expect(cards).toHaveLength(3); // MRR, DAU, MAU
  });
});

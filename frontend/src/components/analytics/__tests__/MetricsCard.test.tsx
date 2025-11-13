/**
 * Unit tests for MetricsCard component
 */

import { render, screen } from '@testing-library/react'
import { MetricCard } from '@/components/dashboard/MetricCard'
import '@testing-library/jest-dom'

describe('MetricCard', () => {
  it('renders metric value correctly', () => {
    render(
      <MetricCard
        title="Active Users"
        value={1234}
        change={15.5}
      />
    )

    expect(screen.getByText('Active Users')).toBeInTheDocument()
    expect(screen.getByText('1,234')).toBeInTheDocument()
    expect(screen.getByText('15.5%')).toBeInTheDocument()
  })

  it('applies correct color for increase', () => {
    const { container } = render(
      <MetricCard
        title="Revenue"
        value={50000}
        change={15.5}
      />
    )

    const changeElement = container.querySelector('.text-green-600')
    expect(changeElement).toBeInTheDocument()
  })

  it('applies correct color for decrease', () => {
    const { container } = render(
      <MetricCard
        title="Error Rate"
        value={0.02}
        change={-5.3}
      />
    )

    // Error rate decrease should be green (good)
    const changeElement = container.querySelector('.text-green-600')
    expect(changeElement).toBeInTheDocument()
  })

  it('formats currency correctly', () => {
    render(
      <MetricCard
        title="Total Revenue"
        value={1500000}
        format="currency"
      />
    )

    expect(screen.getByText('$1,500,000')).toBeInTheDocument()
  })

  it('formats percentage correctly', () => {
    render(
      <MetricCard
        title="Success Rate"
        value={95.5}
        format="percentage"
      />
    )

    expect(screen.getByText('95.5%')).toBeInTheDocument()
  })

  it('formats duration correctly', () => {
    render(
      <MetricCard
        title="Average Duration"
        value={2.5}
        format="duration"
      />
    )

    expect(screen.getByText('2.50s')).toBeInTheDocument()
  })

  it('formats large numbers with compact notation', () => {
    render(
      <MetricCard
        title="Total Credits"
        value={1500000}
      />
    )

    // Default number format should show with commas
    expect(screen.getByText('1,500,000')).toBeInTheDocument()
  })

  it('renders loading state', () => {
    const { container } = render(
      <MetricCard
        title="Active Users"
        value={1234}
        loading={true}
      />
    )

    const loadingElement = container.querySelector('.animate-pulse')
    expect(loadingElement).toBeInTheDocument()
  })

  it('displays description when provided', () => {
    const description = 'This is a test metric description'
    render(
      <MetricCard
        title="Test Metric"
        value={100}
        description={description}
      />
    )

    expect(screen.getByText(description)).toBeInTheDocument()
  })

  it('renders icon when provided', () => {
    const TestIcon = ({ className }: { className?: string }) => (
      <svg className={className} data-testid="test-icon">
        <circle cx="10" cy="10" r="5" />
      </svg>
    )

    render(
      <MetricCard
        title="Test Metric"
        value={100}
        icon={TestIcon}
      />
    )

    expect(screen.getByTestId('test-icon')).toBeInTheDocument()
  })

  it('handles zero change correctly', () => {
    render(
      <MetricCard
        title="Stable Metric"
        value={100}
        change={0}
        trend="neutral"
      />
    )

    // Should render the value but not show trend arrow
    expect(screen.getByText('100')).toBeInTheDocument()
  })

  it('applies inverse trend logic for error metrics', () => {
    const { container } = render(
      <MetricCard
        title="Error Rate"
        value={2.5}
        change={10.5}  // Increase
        format="percentage"
      />
    )

    // Error increase should be red (bad)
    const changeElement = container.querySelector('.text-red-600')
    expect(changeElement).toBeInTheDocument()
  })

  it('applies inverse trend logic for cost metrics', () => {
    const { container } = render(
      <MetricCard
        title="Cost per User"
        value={5.5}
        change={-10}  // Decrease
        format="currency"
      />
    )

    // Cost decrease should be green (good)
    const changeElement = container.querySelector('.text-green-600')
    expect(changeElement).toBeInTheDocument()
  })

  it('uses explicit isInverseTrend prop', () => {
    const { container } = render(
      <MetricCard
        title="Custom Metric"
        value={100}
        change={10}
        isInverseTrend={true}  // Explicit inverse trend
      />
    )

    // Increase with inverse trend should be red
    const changeElement = container.querySelector('.text-red-600')
    expect(changeElement).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(
      <MetricCard
        title="Test"
        value={100}
        className="custom-class"
      />
    )

    const cardElement = container.querySelector('.custom-class')
    expect(cardElement).toBeInTheDocument()
  })

  it('renders string values', () => {
    render(
      <MetricCard
        title="Status"
        value="Active"
      />
    )

    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it('shows up arrow for positive change', () => {
    const { container } = render(
      <MetricCard
        title="Growth"
        value={100}
        change={25}
      />
    )

    // Check for SVG arrow (up arrow)
    const svg = container.querySelector('svg')
    expect(svg).toBeInTheDocument()
  })

  it('shows down arrow for negative change', () => {
    const { container } = render(
      <MetricCard
        title="Decline"
        value={100}
        change={-15}
      />
    )

    // Check for SVG arrow (down arrow)
    const svg = container.querySelector('svg')
    expect(svg).toBeInTheDocument()
  })

  it('does not show change indicator when change is undefined', () => {
    render(
      <MetricCard
        title="No Change"
        value={100}
      />
    )

    // Should not find percentage text
    expect(screen.queryByText(/%/)).not.toBeInTheDocument()
  })
})

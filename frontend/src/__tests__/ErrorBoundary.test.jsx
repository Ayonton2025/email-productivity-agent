import React from 'react'
import { render, screen } from '@testing-library/react'
import ErrorBoundary from '../components/ErrorBoundary.jsx'

function BrokenComponent() {
  throw new Error('render failure')
}

test('renders a recovery view when a child throws', () => {
  const originalError = console.error
  console.error = () => {}

  render(
    <ErrorBoundary>
      <BrokenComponent />
    </ErrorBoundary>
  )

  expect(screen.getByRole('heading', { name: 'Something went wrong' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Reload Application' })).toBeInTheDocument()

  console.error = originalError
})

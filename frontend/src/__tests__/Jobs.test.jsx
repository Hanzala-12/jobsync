import React from 'react'
import { MemoryRouter } from 'react-router-dom'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { buildResumeMock } = vi.hoisted(() => ({
  buildResumeMock: vi.fn().mockResolvedValue({
    data: {
      fixed_resume_text: 'Tailored resume text',
      simple_text_version: 'Tailored resume text',
      html_resume: '<html></html>',
      ats_score: 82,
      validation_passed: true,
      validation_message: 'Consider reducing repetition of keywords; the resume reads a bit dense.',
      changes_made: ['Added keywords'],
    },
  }),
}))

vi.mock('../api/client', () => ({
  API_BASE_URL: '',
  applicationsAPI: {
    create: vi.fn().mockResolvedValue({ data: { id: 1 } }),
    updateStatus: vi.fn().mockResolvedValue({ data: { id: 1 } }),
  },
  jobsAPI: {
    search: vi.fn().mockResolvedValue({
      data: [
        {
          id: 1,
          title: 'Backend Engineer',
          company: 'Acme Corp',
          location: 'Remote',
          description: 'Build Python APIs with FastAPI and SQL',
          source: 'manual',
        },
      ],
    }),
    autocomplete: vi.fn().mockResolvedValue({ data: { suggestions: ['software engineer'] } }),
    match: vi.fn().mockResolvedValue({ data: { match_percentage: 91, explanation: 'Great fit', missing_skills: ['Docker'] } }),
    upsert: vi.fn().mockResolvedValue({ data: { id: 1 } }),
    salaryEstimate: vi.fn().mockResolvedValue({ data: { local_min: 120000, local_max: 220000, remote_min: 1500, remote_max: 3500, market_demand: 'medium', negotiation_tip: 'Use quantified impact.' } }),
  },
  profileAPI: {
    list: vi.fn().mockResolvedValue({ data: { exists: true, selected_profile_id: 1 } }),
  },
  apiActions: {
    buildResume: buildResumeMock,
  },
  getStoredAuthToken: vi.fn().mockReturnValue('token-123'),
  setAuthToken: vi.fn(),
  clearAuthToken: vi.fn(),
}))

vi.mock('../components/ResumeModal', () => ({
  default: ({ open, job }) => (open ? <div data-testid="resume-modal">{job?.title}</div> : null),
}))

import Jobs from '../pages/Jobs'
import { jobsAPI, profileAPI } from '../api/client'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('Jobs page', () => {
  it('renders a job card and opens match/resume actions', async () => {
    render(
      <MemoryRouter initialEntries={['/jobs']}>
        <Jobs />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Acme Corp')).toBeInTheDocument()
    expect(jobsAPI.search).toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Match Me' }))
    expect(await screen.findByText('Great fit')).toBeInTheDocument()
    expect(jobsAPI.match).toHaveBeenCalledWith(1)

    fireEvent.click(screen.getByRole('button', { name: 'Tailor Resume' }))
    expect(await screen.findByTestId('resume-modal')).toHaveTextContent('Backend Engineer')
    expect(profileAPI.list).toHaveBeenCalled()
  })
})

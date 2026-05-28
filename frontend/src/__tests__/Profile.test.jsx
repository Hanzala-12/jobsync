import React from 'react'
import { MemoryRouter } from 'react-router-dom'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { createMock, selectMock } = vi.hoisted(() => ({
  createMock: vi.fn().mockResolvedValue({ data: { profile: { id: 17, full_name: 'Jane Developer' }, message: 'Profile created successfully' } }),
  selectMock: vi.fn().mockResolvedValue({ data: { status: 'success' } }),
}))

vi.mock('../api/client', () => ({
  profileAPI: {
    list: vi.fn().mockResolvedValue({ data: { profiles: [], selected_profile_id: null, total: 0 } }),
    get: vi.fn().mockResolvedValue({ data: null }),
    create: createMock,
    update: vi.fn().mockResolvedValue({ data: { profile: { id: 17 } } }),
    select: selectMock,
    delete: vi.fn().mockResolvedValue({ data: { status: 'success' } }),
  },
}))

import Profile from '../pages/Profile'
import { profileAPI } from '../api/client'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('Profile page', () => {
  it('creates a structured profile with normalized arrays and numbers', async () => {
    render(
      <MemoryRouter initialEntries={['/profile']}>
        <Profile />
      </MemoryRouter>,
    )

    fireEvent.change(await screen.findByPlaceholderText('Your full name'), { target: { value: 'Jane Developer' } })
    fireEvent.change(screen.getByPlaceholderText('you@example.com'), { target: { value: 'jane@example.com' } })
    fireEvent.change(screen.getByPlaceholderText('+92...'), { target: { value: '+92 300 1234567' } })
    fireEvent.change(screen.getByPlaceholderText('City, Country'), { target: { value: 'Karachi' } })
    fireEvent.change(screen.getByPlaceholderText('Write a short profile summary...'), { target: { value: 'Backend engineer' } })

    fireEvent.click(screen.getByRole('tab', { name: 'Skills' }))
    fireEvent.change(screen.getByPlaceholderText('React, FastAPI, SQL, AWS'), { target: { value: 'Python, FastAPI, SQL' } })
    fireEvent.change(screen.getByPlaceholderText('Shipped onboarding flow, led migration, improved ATS score...'), { target: { value: 'Led APIs' } })

    fireEvent.click(screen.getByRole('button', { name: 'Save Profile' }))

    await waitFor(() => expect(createMock).toHaveBeenCalled())
    expect(createMock).toHaveBeenCalledWith(expect.objectContaining({
      full_name: 'Jane Developer',
      email: 'jane@example.com',
      skills: ['Python', 'FastAPI', 'SQL'],
      achievements: ['Led APIs'],
      desired_salary_min: null,
      desired_salary_max: null,
    }))
    expect(selectMock).toHaveBeenCalledWith(17)
    expect(profileAPI.list).toHaveBeenCalled()
  })
})

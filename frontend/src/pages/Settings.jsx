import { useEffect, useMemo, useState } from 'react'
import { ShieldCheck, Trash2 } from 'lucide-react'
import Button from '../components/Button'
import { settingsAPI } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import './Settings.css'

const providers = [
  { key: 'openrouter', label: 'OpenRouter', placeholder: 'sk-or-v1-...' },
  { key: 'groq', label: 'Groq', placeholder: 'gsk_...' },
  { key: 'openai', label: 'OpenAI', placeholder: 'sk-proj-...' },
]

const storageKey = 'jobsync_custom_api_keys'

function Settings() {
  const { handleLogout } = useAuth()
  const [providerState, setProviderState] = useState(() => Object.fromEntries(providers.map((item) => [item.key, { apiKey: '', hasKey: false, saving: false }])))
  const [message, setMessage] = useState('')
  const hasAnyCustomKey = useMemo(() => providers.some((item) => providerState[item.key]?.hasKey), [providerState])

  useEffect(() => {
    const load = async () => {
      try {
        const response = await settingsAPI.listKeys()
        const nextState = Object.fromEntries(providers.map((item) => [item.key, { apiKey: '', hasKey: false, saving: false }]))
        for (const item of response.data || []) {
          const provider = String(item?.provider || '').toLowerCase()
          if (nextState[provider]) {
            nextState[provider].hasKey = Boolean(item?.has_key)
          }
        }
        setProviderState(nextState)
        if (typeof window !== 'undefined') {
          window.localStorage.setItem(storageKey, JSON.stringify(Object.fromEntries(Object.entries(nextState).map(([key, value]) => [key, Boolean(value.hasKey)]))))
        }
      } catch {
        setMessage('Unable to load saved API key status.')
      }
    }

    void load()
  }, [])

  const syncStorage = (nextState) => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(storageKey, JSON.stringify(Object.fromEntries(Object.entries(nextState).map(([key, value]) => [key, Boolean(value.hasKey)]))))
  }

  const updateProvider = (provider, patch) => {
    setProviderState((current) => {
      const next = { ...current, [provider]: { ...current[provider], ...patch } }
      syncStorage(next)
      return next
    })
  }

  const saveKey = async (provider) => {
    const entry = providerState[provider]
    if (!entry?.apiKey?.trim()) {
      setMessage('Enter an API key before saving.')
      return
    }

    updateProvider(provider, { saving: true })
    setMessage('')
    try {
      await settingsAPI.saveKey({ provider, api_key: entry.apiKey.trim() })
      updateProvider(provider, { apiKey: '', hasKey: true, saving: false })
      setMessage(`${provider} key saved.`)
    } catch {
      updateProvider(provider, { saving: false })
      setMessage(`Unable to save ${provider} key.`)
    }
  }

  const deleteKey = async (provider) => {
    updateProvider(provider, { saving: true })
    setMessage('')
    try {
      await settingsAPI.deleteKey(provider)
      updateProvider(provider, { apiKey: '', hasKey: false, saving: false })
      setMessage(`${provider} key removed.`)
    } catch {
      updateProvider(provider, { saving: false })
      setMessage(`Unable to delete ${provider} key.`)
    }
  }

  return (
    <div className="settings-page fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <section
        className="app-card"
        style={{
          padding: 24,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 20,
          flexWrap: 'wrap',
        }}
      >
        <div style={{ minWidth: 0 }}>
          <p style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Account Settings</p>
          <h1 style={{ marginTop: 6 }}>Settings</h1>
          <p className="subtitle">Manage custom API keys for personalized generation. Keys are stored encrypted on the backend and never exposed in full to the browser.</p>
        </div>
        <div
          style={{
            minWidth: 240,
            padding: 16,
            borderRadius: 16,
            background: 'linear-gradient(135deg, rgba(58,87,232,0.10), rgba(16,185,129,0.08))',
            border: '1px solid rgba(58,87,232,0.12)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8, color: 'var(--j-text-1)' }}>
            <ShieldCheck size={18} />
            <strong style={{ fontSize: 14 }}>Provider security</strong>
          </div>
          <p style={{ margin: 0, color: 'var(--j-text-2)', lineHeight: 1.6 }}>{hasAnyCustomKey ? 'Custom provider keys are enabled for this account.' : 'No custom provider keys are saved yet.'}</p>
        </div>
      </section>

      <section
        className="settings-card"
        style={{
          background: 'var(--j-surface)',
          border: '1px solid var(--j-border)',
          borderRadius: 18,
          padding: 24,
          boxShadow: 'var(--j-shadow-sm)',
          display: 'flex',
          flexDirection: 'column',
          gap: 20,
        }}
      >
        {message ? <div className="settings-message" style={{ padding: '12px 14px', borderRadius: 14, background: 'rgba(58,87,232,0.10)', color: 'var(--j-accent)', fontWeight: 600 }}>{message}</div> : null}

        <div className="settings-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16 }}>
          {providers.map((provider) => {
            const state = providerState[provider.key] || {}
            return (
              <div
                key={provider.key}
                className="provider-panel"
                style={{
                  border: '1px solid var(--j-border)',
                  borderRadius: 16,
                  padding: 20,
                  background: state.hasKey ? 'rgba(16,185,129,0.04)' : 'var(--j-surface-2)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 14,
                }}
              >
                <div className="provider-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                  <div>
                    <h2 style={{ fontSize: 18, fontWeight: 800, margin: 0, color: 'var(--j-text-1)' }}>{provider.label}</h2>
                    <p style={{ marginTop: 6, color: 'var(--j-text-2)' }}>{state.hasKey ? 'A custom key is saved.' : 'No key saved yet.'}</p>
                  </div>
                  <span
                    className={`provider-pill ${state.hasKey ? 'active' : ''}`}
                    style={{
                      padding: '6px 10px',
                      borderRadius: 999,
                      fontSize: 12,
                      fontWeight: 700,
                      background: state.hasKey ? 'rgba(16,185,129,0.10)' : 'rgba(148,163,184,0.12)',
                      color: state.hasKey ? '#047857' : 'var(--j-text-2)',
                    }}
                  >
                    {state.hasKey ? 'Saved' : 'Empty'}
                  </span>
                </div>

                <label className="field-label" htmlFor={`${provider.key}-api-key`} style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>API Key</label>
                <input
                  id={`${provider.key}-api-key`}
                  className="text-input"
                  type="password"
                  value={state.apiKey || ''}
                  placeholder={provider.placeholder}
                  onChange={(event) => updateProvider(provider.key, { apiKey: event.target.value })}
                  autoComplete="off"
                  spellCheck="false"
                  style={{ minHeight: 46, borderRadius: 14, border: '1px solid var(--j-border)', background: 'var(--j-surface)', color: 'var(--j-text-1)' }}
                />

                <div className="provider-actions" style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  <Button onClick={() => saveKey(provider.key)} loading={Boolean(state.saving)}>
                    Save Key
                  </Button>
                  <button
                    type="button"
                    className="ghost-button"
                    onClick={() => deleteKey(provider.key)}
                    disabled={Boolean(state.saving) || !state.hasKey}
                    style={{ minHeight: 42, padding: '0 14px', borderRadius: 14, border: '1px solid var(--j-border)', background: 'var(--j-surface)', color: 'var(--j-text-1)', display: 'inline-flex', alignItems: 'center', gap: 8 }}
                  >
                    <Trash2 size={14} />
                    Delete
                  </button>
                </div>
              </div>
            )
          })}
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 16,
            flexWrap: 'wrap',
            padding: 18,
            borderRadius: 16,
            border: '1px solid var(--j-border)',
            background: 'var(--j-surface-2)',
          }}
        >
          <div>
            <p style={{ margin: 0, fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Session</p>
            <h3 style={{ marginTop: 6, fontSize: 16, fontWeight: 800, color: 'var(--j-text-1)' }}>Leave your account</h3>
            <p style={{ marginTop: 6, color: 'var(--j-text-2)' }}>You can sign out from the account menu or here in Settings.</p>
          </div>
          <Button variant="secondary" onClick={() => handleLogout()}>Log out</Button>
        </div>
      </section>
    </div>
  )
}

export default Settings
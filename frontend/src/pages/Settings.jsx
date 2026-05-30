import { useEffect, useMemo, useState } from 'react'
import { ShieldCheck, Trash2 } from 'lucide-react'
import Button from '../components/Button'
import { settingsAPI } from '../api/client'
import './Settings.css'

const providers = [
  { key: 'openrouter', label: 'OpenRouter', placeholder: 'sk-or-v1-...' },
  { key: 'groq', label: 'Groq', placeholder: 'gsk_...' },
  { key: 'openai', label: 'OpenAI', placeholder: 'sk-proj-...' },
]

const storageKey = 'jobsync_custom_api_keys'

function Settings() {
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
    <div className="settings-page fade-up">
      <div className="page-header">
        <h1>Settings</h1>
        <p className="subtitle">Manage custom API keys for personalized generation. Keys are stored encrypted on the backend and never exposed in full to the browser.</p>
      </div>

      <section className="settings-card">
        <div className="settings-banner">
          <ShieldCheck size={18} />
          <span>{hasAnyCustomKey ? 'Custom provider keys are enabled for this account.' : 'No custom provider keys are saved yet.'}</span>
        </div>

        {message ? <div className="settings-message">{message}</div> : null}

        <div className="settings-grid">
          {providers.map((provider) => {
            const state = providerState[provider.key] || {}
            return (
              <div key={provider.key} className="provider-panel">
                <div className="provider-header">
                  <div>
                    <h2>{provider.label}</h2>
                    <p>{state.hasKey ? 'A custom key is saved.' : 'No key saved yet.'}</p>
                  </div>
                  <span className={`provider-pill ${state.hasKey ? 'active' : ''}`}>{state.hasKey ? 'Saved' : 'Empty'}</span>
                </div>

                <label className="field-label" htmlFor={`${provider.key}-api-key`}>API Key</label>
                <input
                  id={`${provider.key}-api-key`}
                  className="text-input"
                  type="password"
                  value={state.apiKey || ''}
                  placeholder={provider.placeholder}
                  onChange={(event) => updateProvider(provider.key, { apiKey: event.target.value })}
                  autoComplete="off"
                  spellCheck="false"
                />

                <div className="provider-actions">
                  <Button onClick={() => saveKey(provider.key)} loading={Boolean(state.saving)}>
                    Save Key
                  </Button>
                  <button type="button" className="ghost-button" onClick={() => deleteKey(provider.key)} disabled={Boolean(state.saving) || !state.hasKey}>
                    <Trash2 size={14} />
                    Delete
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </section>
    </div>
  )
}

export default Settings
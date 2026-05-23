// Manages job-search requests and keeps the Jobs page loading state in sync.
const state = {
  jobs: [],
  streamingCount: 0,
  streamElapsed: 0,
  loading: false,
  url: null,
  timer: null,
  subscribers: new Set(),
}

function notify() {
  const snapshot = {
    jobs: [...state.jobs],
    streamingCount: state.streamingCount,
    streamElapsed: state.streamElapsed,
    loading: state.loading,
    url: state.url,
  }
  for (const cb of state.subscribers) {
    try {
      cb(snapshot)
    } catch (e) {
      // ignore subscriber errors
    }
  }
}

function resetStreamState() {
  if (state.timer) {
    clearInterval(state.timer)
    state.timer = null
  }
  state.loading = false
  state.url = null
}

async function start(url) {
  if (state.url === url && state.loading) return

  if (state.timer) {
    clearInterval(state.timer)
    state.timer = null
  }

  state.jobs = []
  state.streamingCount = 0
  state.streamElapsed = 0
  state.loading = true
  state.url = url

  state.timer = setInterval(() => {
    if (!state.loading) return
    state.streamElapsed += 1
    notify()
  }, 1000)

  notify()

  try {
    const fallbackUrl = url.replace('/search/stream', '/search')
    const response = await fetch(fallbackUrl, {
      headers: {
        Accept: 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`SearchStream HTTP ${response.status}`)
    }

    const jobs = await response.json()
    if (!Array.isArray(jobs)) {
      throw new Error('SearchStream payload was not an array')
    }

    state.jobs = jobs
    state.streamingCount = jobs.length
    state.loading = false
    if (state.timer) {
      clearInterval(state.timer)
      state.timer = null
    }
    notify()
  } catch (error) {
    console.error('SearchStream error', error)
    state.loading = false
    if (state.timer) {
      clearInterval(state.timer)
      state.timer = null
    }
    notify()
  }
}

function subscribe(cb) {
  state.subscribers.add(cb)
  try {
    cb({ jobs: [...state.jobs], streamingCount: state.streamingCount, streamElapsed: state.streamElapsed, loading: state.loading, url: state.url })
  } catch (e) {}
  return () => {
    state.subscribers.delete(cb)
  }
}

function stop() {
  resetStreamState()
  notify()
}

function getState() {
  return {
    jobs: [...state.jobs],
    streamingCount: state.streamingCount,
    streamElapsed: state.streamElapsed,
    loading: state.loading,
    url: state.url,
  }
}

export default { start, subscribe, stop, getState }

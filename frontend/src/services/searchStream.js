// Simple singleton manager for job search SSE streams
const state = {
  es: null,
  jobs: [],
  streamingCount: 0,
  streamElapsed: 0,
  loading: false,
  url: null,
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
    try { cb(snapshot) } catch (e) { /* ignore */ }
  }
}

function start(url) {
  if (state.es && state.url === url) return
  if (state.es) {
    try { state.es.close() } catch (e) {}
    state.es = null
  }
  state.jobs = []
  state.streamingCount = 0
  state.streamElapsed = 0
  state.loading = true
  state.url = url

  try {
    const es = new EventSource(url)
    state.es = es

    es.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data)
        if (typeof data.combined_count === 'number') state.streamingCount = data.combined_count
        if (typeof data.elapsed === 'number') state.streamElapsed = data.elapsed
        if (data.partial && Array.isArray(data.partial)) {
          for (const j of data.partial) {
            state.jobs.push(j)
          }
        }
        if (data.done) {
          state.loading = false
          try { es.close() } catch (e) {}
          state.es = null
        }
        notify()
      } catch (e) {
        console.error('SearchStream parse error', e)
      }
    }

    es.onerror = (err) => {
      console.error('SearchStream error', err)
      state.loading = false
      try { es.close() } catch (e) {}
      state.es = null
      notify()
    }
  } catch (e) {
    console.error('SearchStream start failed', e)
    state.loading = false
    notify()
  }
}

function subscribe(cb) {
  state.subscribers.add(cb)
  // send initial snapshot
  try { cb({ jobs: [...state.jobs], streamingCount: state.streamingCount, streamElapsed: state.streamElapsed, loading: state.loading, url: state.url }) } catch (e) {}
  return () => { state.subscribers.delete(cb) }
}

function stop() {
  if (state.es) {
    try { state.es.close() } catch (e) {}
    state.es = null
  }
  state.loading = false
  state.url = null
  notify()
}

function getState() {
  return { jobs: [...state.jobs], streamingCount: state.streamingCount, streamElapsed: state.streamElapsed, loading: state.loading, url: state.url }
}

export default { start, subscribe, stop, getState }

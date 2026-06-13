// frontend/src/hooks/useApi.js
import { useState, useEffect } from 'react'

export function useApi(apiFn, mockData, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isMock, setIsMock] = useState(false)
  const [tick, setTick] = useState(0)

  function refetch() {
    setTick(t => t + 1)
  }

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    apiFn()
      .then(result => {
        if (!cancelled) {
          setData(result)
          setError(null)
          setIsMock(false)
        }
      })
      .catch(err => {
        if (!cancelled) {
          if (mockData !== undefined && mockData !== null) {
            setData(mockData)
            setIsMock(true)
            setError(null)
          } else {
            setError(err.message)
            setIsMock(false)
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])

  return { data, loading, error, isMock, refetch }
}
